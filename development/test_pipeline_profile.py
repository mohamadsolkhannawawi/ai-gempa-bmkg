import unittest
from pipeline_profile import (PLANS, Profile, build_default_catalog, compile_pipeline, to_legacy_keys, validate)

CAT = build_default_catalog()
codes = lambda issues, sev="error": sorted({i.code for i in issues if i.severity == sev})
P = lambda d: Profile.from_dict(d)
PICK_ONLY = {"mode": "custom", "name": "pick saja",
             "stages": {"ingest": {"provider": "seedlink_v3"}, "p_pick": {"provider": "phasenet"}},
             "sinks": {"webhook": {"params": {"url": "https://x.io/h", "artifacts": ["pick"]}}}}


class T(unittest.TestCase):
    def test_default_valid_and_legacy_topics(self):
        c = compile_pipeline(Profile("default"), CAT, PLANS["basic"])
        self.assertTrue(c["ok"])
        self.assertEqual([s["stage"] for s in c["stages"]], ["ingest", "p_pick", "association", "locmag"])
        self.assertIn("waveform_seedlink", c["topics"]); self.assertIn("event_topic", c["topics"])
        self.assertEqual([s["sink"] for s in c["sinks"]], ["archive", "ws_ui"])
        self.assertEqual(c["warnings"], [])

    def test_default_rejects_overrides(self):
        i = validate(P({"mode": "default", "stages": {"p_pick": {"provider": "sta_lta"}}}), CAT, PLANS["pro"])
        self.assertIn("V010", codes(i))

    def test_custom_pick_only_service(self):
        c = compile_pipeline(P(PICK_ONLY), CAT, PLANS["pro"])
        self.assertTrue(c["ok"], c)
        self.assertEqual([s["stage"] for s in c["stages"]], ["ingest", "p_pick"])
        self.assertEqual(c["sinks"][0]["consume"], ["pick_topic"])
        self.assertNotIn("cluster_topic", c["topics"])
        self.assertEqual(c["stages"][1]["params"]["p_threshold"], 0.3)   # default skema terisi

    def test_association_only_with_external_picks(self):
        c = compile_pipeline(P({"mode": "custom", "external_inputs": ["pick"],
                                "stages": {"association": {"provider": "dbscan_simple"}, "locmag": {"provider": "geiger"}},
                                "sinks": {"ws_ui": {}}}), CAT, PLANS["pro"])
        self.assertTrue(c["ok"], c)
        self.assertEqual(c["stages"][0]["consume"], ["pick_topic"])

    def test_missing_input_and_no_source(self):
        i = validate(P({"mode": "custom", "stages": {"association": {"provider": "dbscan_simple"}},
                        "sinks": {"ws_ui": {"params": {"artifacts": ["cluster"]}}}}), CAT, PLANS["pro"])
        self.assertTrue({"V004", "V005"} <= set(codes(i)))

    def test_sink_rules(self):
        i = validate(P({**PICK_ONLY, "sinks": {}}), CAT, PLANS["pro"])
        self.assertIn("V006", codes(i))
        d = dict(PICK_ONLY); d["sinks"] = {"webhook": {"params": {"url": "https://x.io", "artifacts": ["event"]}}}
        self.assertIn("V007", codes(validate(P(d), CAT, PLANS["pro"])))

    def test_param_validation(self):
        def bad(params, prov="phasenet"):
            d = {"mode": "custom", "stages": {"ingest": {"provider": "seedlink_v3"}, "p_pick": {"provider": prov, "params": params}},
                 "sinks": {"webhook": {"params": {"url": "https://x.io", "artifacts": ["pick"]}}}}
            return codes(validate(P(d), CAT, PLANS["pro"]))
        self.assertEqual(bad({"p_threshold": 1.5}), ["V003"])        # di luar rentang
        self.assertEqual(bad({"p_threshold": "tinggi"}), ["V003"])   # tipe salah
        self.assertEqual(bad({"weights": "ngawur"}), ["V003"])       # enum salah
        self.assertEqual(bad({"batch_size": 2.5}), ["V003"])         # integer
        self.assertEqual(bad({"foo": 1}), ["V003"])                  # parameter tidak dikenal
        self.assertEqual(bad({"p_threshold": 0.4}), [])

    def test_required_param(self):
        d = dict(PICK_ONLY); d["sinks"] = {"webhook": {"params": {"artifacts": ["pick"]}}}
        self.assertIn("V003", codes(validate(P(d), CAT, PLANS["pro"])))

    def test_plan_rules(self):
        self.assertIn("V009", codes(validate(P(PICK_ONLY), CAT, PLANS["basic"])))
        d = {"mode": "custom", "stages": {"ingest": {"provider": "seedlink_v3"}, "p_pick": {"provider": "phasenet"},
                                          "association": {"provider": "pyocto"}},
             "sinks": {"ws_ui": {"params": {"artifacts": ["cluster"]}}}}
        self.assertIn("V008", codes(validate(P(d), CAT, PLANS["pro"])))            # experimental -> enterprise
        self.assertNotIn("V008", codes(validate(P(d), CAT, PLANS["enterprise"])))

    def test_unknown_names(self):
        i = validate(P({"mode": "custom", "stages": {"xyz": {"provider": "a"}, "p_pick": {"provider": "nope"}},
                        "sinks": {"ws_ui": {}}}), CAT, PLANS["pro"])
        self.assertTrue({"V001", "V002"} <= set(codes(i)))

    def test_warnings(self):
        d = {"mode": "custom", "stages": {"ingest": {"provider": "seedlink_v3"}, "p_pick": {"provider": "phasenet"},
                                          "association": {"provider": "dbscan_simple"}}, "sinks": {"ws_ui": {"params": {"artifacts": ["pick"]}}}}
        self.assertIn("W001", codes(validate(P(d), CAT, PLANS["pro"]), "warning"))   # cluster/arrival tak dipakai
        d2 = dict(PICK_ONLY); d2["external_inputs"] = ["pick"]
        self.assertIn("W003", codes(validate(P(d2), CAT, PLANS["pro"]), "warning"))

    def test_disabled_stage_ignored(self):
        d = dict(PICK_ONLY); d["stages"] = {**PICK_ONLY["stages"], "association": {"enabled": False, "provider": "nope"}}
        self.assertTrue(compile_pipeline(P(d), CAT, PLANS["pro"])["ok"])

    def test_rev_deterministic(self):
        a = compile_pipeline(P(PICK_ONLY), CAT, PLANS["pro"])["rev"]
        d = {"sinks": PICK_ONLY["sinks"], "stages": dict(reversed(list(PICK_ONLY["stages"].items()))), "name": "x", "mode": "custom"}
        self.assertEqual(a, compile_pipeline(P(d), CAT, PLANS["pro"])["rev"])
        d["stages"]["p_pick"] = {"provider": "phasenet", "params": {"p_threshold": 0.31}}
        self.assertNotEqual(a, compile_pipeline(P(d), CAT, PLANS["pro"])["rev"])

    def test_workspace_topics(self):
        c = compile_pipeline(P(PICK_ONLY), CAT, PLANS["pro"], workspace="acme")
        self.assertEqual(c["sinks"][0]["consume"], ["acme.pick"]); self.assertEqual(c["stages"][0]["consumer_group"], "acme.ingest")

    def test_legacy_projection(self):
        keys = {k["name"]: k["config"] for k in to_legacy_keys(compile_pipeline(P(PICK_ONLY), CAT, PLANS["pro"]))}
        self.assertEqual(keys["ai.ppick.provider"], "phasenet"); self.assertEqual(keys["ai.ppick.p_threshold"], 0.3)
        self.assertFalse(keys["ai.association.enabled"]); self.assertFalse(keys["ai.locmag.enabled"]); self.assertIn("pipeline.rev", keys)


if __name__ == "__main__":
    unittest.main()
