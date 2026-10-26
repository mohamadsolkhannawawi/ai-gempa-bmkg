"""
tests/unit/test_profile.py - Unit tests untuk core/profile.py.
"""
import sys
sys.path.insert(0, "..")  # allow import core

from datetime import datetime, timezone
from decimal import Decimal
import json
import pytest

from core.profile import (
    Profile, StageCfg, SinkCfg, Catalog, Provider, WorkspacePlan, Artifact,
    ProfileService, ProfileIssue, IssueSeverity
)


class TestProfile:
    """Test Profile entity."""
    
    def test_default_mode_fixed(self):
        """Default mode = fixed preset, tidak boleh ada override."""
        p = Profile(
            workspace_id="ws1",
            mode="default",
            stages={
                "ingest": StageCfg(enabled=True, provider="seedlink_v3"),
                "p_pick": StageCfg(enabled=True, provider="sta_lta"),
            },
            sinks=[SinkCfg(type="ws_ui")],
            external_inputs=[]
        )
        assert p.mode == "default"
        assert p.stages["ingest"].provider == "seedlink_v3"
        # Default mode tidak bisa ubah provider di runtime
        # ponytail: check dilakukan validation service, bukan entity
    
    def test_custom_mode_requires_plan(self):
        """Custom mode hanya untuk plan Pro/Enterprise."""
        # Custom dengan plan Basic akan gagal validation
        # Test di ProfileService.validation
        
    def test_missing_dependency_issue(self):
        """Stage p_pick butuh waveform dari ingest."""
        p = Profile(
            workspace_id="ws1",
            mode="default",
            stages={
                "p_pick": StageCfg(enabled=True, provider="sta_lta"),
            },
            sinks=[SinkCfg(type="ws_ui")],
            external_inputs=[]
        )
        # p_pick butuh ingest, tapi ingest disabled → error
        # ponytail: validation service check dependency graph
    
    def test_to_dict(self):
        """Profile serialize ke dict."""
        p = Profile(
            workspace_id="ws1",
            mode="custom",
            stages={
                "ingest": StageCfg(enabled=True, provider="seedlink_v3"),
            },
            sinks=[SinkCfg(type="ws_ui", topic="out")],
            external_inputs=[]
        )
        d = p.to_dict()
        assert d["workspace_id"] == "ws1"
        assert d["mode"] == "custom"
        assert d["stages"]["ingest"]["enabled"] == True
        assert d["sinks"][0]["type"] == "ws_ui"


class TestStageCfg:
    """Test StageCfg value object."""
    
    def test_stage_enabled(self):
        stage = StageCfg(enabled=True, provider="phasenet", params={"threshold": 0.5})
        assert stage.enabled == True
        assert stage.provider == "phasenet"
        assert stage.params["threshold"] == 0.5
    
    def test_stage_disabled(self):
        stage = StageCfg(enabled=False, provider="", params={})
        assert stage.enabled == False
        # disabled stage boleh kosong provider
        assert stage.provider == ""


class TestCatalog:
    """Test Catalog domain service."""
    
    def test_available_providers(self):
        """Catalog punya mapping stage → providers."""
        cat = Catalog()
        # Catalog is static (hard-coded) for now
        assert "ingest" in cat.providers
        assert "p_pick" in cat.providers
        assert "phasenet" in cat.providers["p_pick"]
        assert "sta_lta" in cat.providers["p_pick"]
    
    def test_provider_details(self):
        """Provider punya metadata."""
        phasenet = cat.providers["p_pick"]["phasenet"]
        assert phasenet["version"] == "2.0"
        assert phasenet["tier"] == "GPU_BASIC"
        assert "gpu_memory" in phasenet["resources"]


class TestProfileService:
    """Test ProfileService domain service."""
    
    def test_validate_profile_missing_sink(self):
        """Profile harus punya minimal 1 sink aktif."""
        p = Profile(
            workspace_id="ws1",
            mode="default",
            stages={
                "ingest": StageCfg(enabled=True, provider="seedlink_v3"),
                "p_pick": StageCfg(enabled=True, provider="sta_lta"),
            },
            sinks=[],  # no sink → error
            external_inputs=[]
        )
        issues = ProfileService.validate_profile(p, Catalog(), WorkspacePlan.BASIC)
        assert len(issues) > 0
        assert any(i.severity == IssueSeverity.ERROR and "sink" in i.message for i in issues)
    
    def test_validate_custom_mode_basic_plan(self):
        """Basic plan tidak boleh pakai custom mode."""
        p = Profile(
            workspace_id="ws1",
            mode="custom",  # custom
            stages={
                "ingest": StageCfg(enabled=True, provider="seedlink_v3"),
            },
            sinks=[SinkCfg(type="ws_ui")],
            external_inputs=[]
        )
        issues = ProfileService.validate_profile(p, Catalog(), WorkspacePlan.BASIC)
        assert len(issues) > 0
        assert any(i.code == "P002" for i in issues)  # P002 = custom requires Pro/Enterprise
    
    def test_validate_provider_not_in_catalog(self):
        """Provider harus ada di catalog."""
        p = Profile(
            workspace_id="ws1",
            mode="default",
            stages={
                "ingest": StageCfg(enabled=True, provider="seedlink_v3"),
                "p_pick": StageCfg(enabled=True, provider="unknown_provider"),  # not in catalog
            },
            sinks=[SinkCfg(type="ws_ui")],
            external_inputs=[]
        )
        issues = ProfileService.validate_profile(p, Catalog(), WorkspacePlan.PRO)
        assert len(issues) > 0
        assert any("unknown_provider" in i.message for i in issues)
    
    def test_validate_dependency_chain(self):
        """Stage dependency harus terpenuhi."""
        p = Profile(
            workspace_id="ws1",
            mode="default",
            stages={
                # p_pick butuh waveform dari ingest, tapi ingest disabled
                "ingest": StageCfg(enabled=False, provider="seedlink_v3"),
                "p_pick": StageCfg(enabled=True, provider="sta_lta"),
            },
            sinks=[SinkCfg(type="ws_ui")],
            external_inputs=[]
        )
        issues = ProfileService.validate_profile(p, Catalog(), WorkspacePlan.PRO)
        assert len(issues) > 0
        assert any("ingest" in i.message and "p_pick" in i.message for i in issues)
    
    def test_validate_free_quota_exceed(self):
        """Provider GPU exceed free quota untuk trial."""
        p = Profile(
            workspace_id="ws1",
            mode="default",
            stages={
                "ingest": StageCfg(enabled=True, provider="seedlink_v3"),
                "p_pick": StageCfg(enabled=True, provider="phasenet"),  # GPU
            },
            sinks=[SinkCfg(type="ws_ui")],
            external_inputs=[]
        )
        issues = ProfileService.validate_profile(p, Catalog(), WorkspacePlan.BASIC, is_trial=True)
        assert len(issues) > 0
        assert any("free quota" in i.message for i in issues)
    
    def test_compile_pipeline(self):
        """Compile profile ke pipeline topics + stages."""
        p = Profile(
            workspace_id="ws1",
            mode="default",
            stages={
                "ingest": StageCfg(enabled=True, provider="seedlink_v3"),
                "p_pick": StageCfg(enabled=True, provider="sta_lta"),
            },
            sinks=[SinkCfg(type="ws_ui"), SinkCfg(type="webhook", url="https://example.com")],
            external_inputs=[]
        )
        compiled = ProfileService.compile_pipeline(p, Catalog(), "ws1")
        assert "topics" in compiled
        assert "stages" in compiled
        assert "rev" in compiled
        assert len(compiled["rev"]) == 12  # SHA256 short hash
        
        # Topics: waveform, pick
        topics = [t["name"] for t in compiled["topics"]]
        assert "ws1.waveform" in topics
        assert "ws1.pick" in topics
        
        # Sinks: ws_ui, webhook
        sinks = [s["type"] for s in compiled["sinks"]]
        assert "ws_ui" in sinks
        assert "webhook" in sinks
    
    def test_compile_custom_topic_prefix(self):
        """Custom workspace topic prefix {workspace}.{artifact}."""
        p = Profile(
            workspace_id="acme",
            mode="custom",
            stages={
                "ingest": StageCfg(enabled=True, provider="seedlink_v3"),
                "p_pick": StageCfg(enabled=True, provider="sta_lta"),
            },
            sinks=[SinkCfg(type="ws_ui")],
            external_inputs=[]
        )
        compiled = ProfileService.compile_pipeline(p, Catalog(), "acme")
        topics = [t["name"] for t in compiled["topics"]]
        # Topic naming: workspace.artifact
        assert any(t.startswith("acme.") for t in topics)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
