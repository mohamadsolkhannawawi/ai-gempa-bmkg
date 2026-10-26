"""
core/event.py - Event Detection Domain untuk AI-GEMPA (tanpa framework).

Konsep:
  - Waveform  : raw seismic signal dari SeedLink/FDSN, 3-channel (BHZ, BHN, BHE or HHZ, HHN, HHE)
  - Pick      : P-wave atau S-wave arrival time + confidence
  - Cluster   : group picks yang berkaitan (spatial + temporal proximity)
  - Arrival   : refined pick post-association (phase, quality)
  - Event     : located earthquake = Cluster + LocMag result (lat, lon, depth, magnitude)

Lifecycle:
  Waveform [continuous stream] → Pick [1 pick per channel+phase] → Cluster [N picks] → Event [1 event]
  
Naming:
  - net.sta.cha : network.station.channel (e.g., IA.BMKG.BHZ, IA.CIWI.HHZ)
  - Timestamp   : UTC in ISO8601 format (e.g., 2026-10-19T12:33:08.465Z)
  - Magnitude   : local (ML), body (mb), surface (Ms) wave
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple
import hashlib
import json


# ----------------------------------------------------------------------------- enum
class Phase(str, Enum):
    """Seismic wave phase."""
    P = "P"
    S = "S"
    PP = "PP"
    SS = "SS"
    PcP = "PcP"


class Quality(str, Enum):
    """Pick quality (confidence) level."""
    EXCELLENT = "excellent"     # confidence >= 0.95
    GOOD = "good"               # confidence >= 0.80
    FAIR = "fair"               # confidence >= 0.60
    POOR = "poor"               # confidence < 0.60


class MagnitudeType(str, Enum):
    """Magnitude scale."""
    ML = "ML"        # local magnitude (Richter)
    mb = "mb"        # body-wave magnitude
    Ms = "Ms"        # surface-wave magnitude
    Mw = "Mw"        # moment magnitude
    MW_CUSTOM = "Mw_custom"  # custom computed


class EventStatus(str, Enum):
    """Event lifecycle status."""
    PRELIMINARY = "preliminary"  # initial location
    REVISED = "revised"          # updated location
    CONFIRMED = "confirmed"      # manual review + QA
    RETRACTED = "retracted"      # false alarm


# ----------------------------------------------------------------------------- value object
@dataclass(frozen=True)
class Timestamp:
    """UTC timestamp dengan nanosecond precision."""
    iso8601: str                                # e.g., "2026-10-19T12:33:08.465123Z"
    
    @staticmethod
    def from_datetime(dt: datetime) -> Timestamp:
        """Create dari Python datetime (assumed UTC)."""
        if not dt.tzinfo:
            raise ValueError("datetime harus timezone-aware (UTC)")
        iso = dt.isoformat(timespec="microseconds").replace("+00:00", "Z")
        return Timestamp(iso)
    
    def to_datetime(self) -> datetime:
        return datetime.fromisoformat(self.iso8601.replace("Z", "+00:00"))
    
    def __str__(self) -> str:
        return self.iso8601


@dataclass(frozen=True)
class Location:
    """Earthquake epicenter (lat, lon, depth)."""
    latitude: Decimal              # degrees, -90 to +90 (negative = South)
    longitude: Decimal             # degrees, -180 to +180 (negative = West)
    depth: Decimal                 # km, typically 0-700
    uncertainty_lat: Decimal = Decimal("0")     # km, error estimate
    uncertainty_lon: Decimal = Decimal("0")
    uncertainty_depth: Decimal = Decimal("0")
    
    def __post_init__(self):
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"latitude {self.latitude} out of range [-90, 90]")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"longitude {self.longitude} out of range [-180, 180]")
        if self.depth < 0:
            raise ValueError(f"depth {self.depth} must be >= 0")
    
    def distance_to(self, other: Location) -> Decimal:
        """Approximate distance (km) using Haversine formula."""
        # ponytail: simplified, not exact (good enough for clustering)
        lat1, lon1 = float(self.latitude), float(self.longitude)
        lat2, lon2 = float(other.latitude), float(other.longitude)
        from math import radians, sin, cos, sqrt, atan2
        R = 6371  # Earth radius km
        dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return Decimal(R * c)


@dataclass(frozen=True)
class Magnitude:
    """Earthquake magnitude."""
    value: Decimal              # e.g., 5.2
    type: MagnitudeType         # ML, mb, Ms, Mw
    uncertainty: Decimal = Decimal("0.1")  # typical uncertainty
    author: str = "auto"        # who computed (auto|BMKG|USGS)
    
    def __post_init__(self):
        if self.value < -2 or self.value > 10:
            raise ValueError(f"magnitude {self.value} unlikely")


@dataclass(frozen=True)
class Channel:
    """Seismic channel identifier."""
    network: str               # e.g., "IA" (network code)
    station: str               # e.g., "BMKG" (station code)
    channel: str               # e.g., "BHZ" (3 chars: band + instrument + direction)
    
    def to_str(self) -> str:
        return f"{self.network}.{self.station}.{self.channel}"
    
    @staticmethod
    def from_str(s: str) -> Channel:
        parts = s.split(".")
        if len(parts) != 3:
            raise ValueError(f"invalid channel format: {s}")
        return Channel(parts[0], parts[1], parts[2])


# ----------------------------------------------------------------------------- entity
@dataclass
class Waveform:
    """Raw seismic signal stream."""
    workspace_id: str
    channel: Channel
    start_time: Timestamp
    end_time: Timestamp
    sample_rate: int            # Hz
    samples: List[float]        # voltage or counts
    unit: str = "counts"        # or "velocity" (m/s)
    
    def duration_sec(self) -> Decimal:
        t_start = self.start_time.to_datetime()
        t_end = self.end_time.to_datetime()
        return Decimal((t_end - t_start).total_seconds())
    
    def rms(self) -> float:
        """RMS (root-mean-square) amplitude."""
        if not self.samples:
            return 0.0
        mean_sq = sum(x**2 for x in self.samples) / len(self.samples)
        return mean_sq ** 0.5


@dataclass
class Pick:
    """P-wave or S-wave arrival time detection."""
    workspace_id: str
    event_id: str = ""          # empty = unassociated
    channel: Channel = None
    phase: Phase = Phase.P
    time: Timestamp = None      # arrival time (UTC)
    confidence: Decimal = Decimal("0.5")  # 0-1, output dari neural network
    residual: Decimal = Decimal("0")      # observed - theoretical time (sec)
    author: str = "auto"        # "phasenet" | "sta_lta" | "manual"
    
    @property
    def quality(self) -> Quality:
        """Infer quality dari confidence."""
        conf = float(self.confidence)
        if conf >= 0.95:
            return Quality.EXCELLENT
        elif conf >= 0.80:
            return Quality.GOOD
        elif conf >= 0.60:
            return Quality.FAIR
        return Quality.POOR
    
    def to_dict(self) -> Dict:
        return {
            "channel": self.channel.to_str() if self.channel else None,
            "phase": self.phase.value,
            "time": str(self.time),
            "confidence": float(self.confidence),
            "quality": self.quality.value,
            "author": self.author
        }


@dataclass
class Cluster:
    """Grouped picks (spatial + temporal proximity) representing 1 earthquake."""
    workspace_id: str
    cluster_id: str             # UUID
    pick_ids: List[str] = field(default_factory=list)  # ref to Pick
    centroid_time: Timestamp = None      # mean pick time
    centroid_location: Location = None   # initial epicenter estimate
    n_stations: int = 0
    time_span: Decimal = Decimal("30")  # sec, typical P-S window
    
    def rms_residual(self) -> Decimal:
        """Average pick residual in cluster."""
        # ponytail: placeholder, actual = get picks from DB, compute mean
        return Decimal("1.5")  # typical ~1-2 sec


@dataclass
class Arrival:
    """Refined pick post-association (high-quality pick for location)."""
    workspace_id: str
    pick_id: str                # ref to Pick
    channel: Channel
    phase: Phase
    time: Timestamp
    quality: Quality
    distance_deg: Decimal = Decimal("0")  # epicentral distance (if known)
    takeoff_angle: Decimal = Decimal("0")  # ray angle at source


@dataclass
class Event:
    """Located earthquake."""
    workspace_id: str
    event_id: str               # UUID
    status: EventStatus = EventStatus.PRELIMINARY
    origin_time: Timestamp = None      # earthquake time (UTC)
    location: Location = None
    magnitude: Magnitude = None
    arrivals: List[Arrival] = field(default_factory=list)
    n_arrivals: int = 0
    depth_type: str = "from_location"  # "from_location" | "fixed" | "depth_phases"
    quality_indicator: str = "A"  # A=best, D=worst (per USGS)
    rms_residual: Decimal = Decimal("0")
    created_at: Timestamp = None
    updated_at: Timestamp = None
    source: str = "auto"        # "auto" | "manual_review" | "icsc"
    
    def to_dict(self) -> Dict:
        return {
            "event_id": self.event_id,
            "status": self.status.value,
            "origin_time": str(self.origin_time),
            "location": {
                "latitude": float(self.location.latitude),
                "longitude": float(self.location.longitude),
                "depth": float(self.location.depth),
            },
            "magnitude": {
                "value": float(self.magnitude.value),
                "type": self.magnitude.type.value,
            },
            "n_arrivals": self.n_arrivals,
            "quality": self.quality_indicator,
            "created_at": str(self.created_at),
        }


# ----------------------------------------------------------------------------- repository interface
class EventRepository:
    """Interface untuk Event persistence."""
    
    def save_waveform(self, wf: Waveform) -> str:
        """Save waveform, return waveform_id."""
        raise NotImplementedError
    
    def save_pick(self, pick: Pick) -> str:
        """Save pick, return pick_id."""
        raise NotImplementedError
    
    def save_cluster(self, cluster: Cluster) -> str:
        """Save cluster, return cluster_id."""
        raise NotImplementedError
    
    def save_event(self, event: Event) -> str:
        """Save event, return event_id."""
        raise NotImplementedError
    
    def get_event(self, event_id: str) -> Optional[Event]:
        """Retrieve event by ID."""
        raise NotImplementedError
    
    def get_latest_event(self, workspace_id: str, limit: int = 10) -> List[Event]:
        """Get N latest events for workspace."""
        raise NotImplementedError
    
    def get_picks_for_cluster(self, cluster_id: str) -> List[Pick]:
        """Get all picks in cluster."""
        raise NotImplementedError


# ----------------------------------------------------------------------------- domain service
class EventAssemblyService:
    """Pure business logic untuk assemble Event dari Cluster + LocMag result."""
    
    @staticmethod
    def create_event_from_cluster(cluster: Cluster, location: Location, 
                                 magnitude: Magnitude, arrivals: List[Arrival]) -> Event:
        """Create Event dari hasil association + location."""
        if not cluster.centroid_time:
            raise ValueError("cluster harus punya centroid_time")
        
        event = Event(
            workspace_id=cluster.workspace_id,
            event_id=__import__("uuid").uuid4().hex[:12],
            status=EventStatus.PRELIMINARY,
            origin_time=cluster.centroid_time,
            location=location,
            magnitude=magnitude,
            arrivals=arrivals,
            n_arrivals=len(arrivals),
            created_at=Timestamp.from_datetime(datetime.now(__import__("datetime").timezone.utc))
        )
        return event
    
    @staticmethod
    def event_hash(event: Event) -> str:
        """Create immutable hash dari event (untuk revision tracking)."""
        body = {
            "origin_time": str(event.origin_time),
            "lat": float(event.location.latitude),
            "lon": float(event.location.longitude),
            "depth": float(event.location.depth),
            "magnitude": float(event.magnitude.value),
            "n_arrivals": event.n_arrivals,
        }
        return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:12]


# ----------------------------------------------------------------------------- aggregate
@dataclass
class EventAggregate:
    """Aggregate root untuk Event + Cluster + Arrivals (1 seismic event)."""
    event: Event
    cluster: Cluster
    arrivals: List[Arrival]
    
    def to_quakeml_dict(self) -> Dict:
        """Export ke format QuakeML-compatible (untuk USGS/EMSC compatibility)."""
        return {
            "type": "QuakeML",
            "event": self.event.to_dict(),
            "arrivals": [{"channel": a.channel.to_str(), "phase": a.phase.value, 
                         "time": str(a.time), "quality": a.quality.value} for a in self.arrivals],
        }


if __name__ == "__main__":
    # Example: create waveform → pick → cluster → event
    ch = Channel("IA", "BMKG", "BHZ")
    t = Timestamp("2026-10-19T12:33:08.465123Z")
    wf = Waveform("workspace1", ch, t, Timestamp("2026-10-19T12:35:00Z"), 100, [0.1]*200)
    
    pick = Pick("workspace1", channel=ch, phase=Phase.P, time=t, confidence=Decimal("0.94"))
    print(f"Pick: {pick.phase} @ {pick.time}, quality={pick.quality}")
    
    loc = Location(Decimal("-6.5"), Decimal("107.3"), Decimal("15"))
    mag = Magnitude(Decimal("5.2"), MagnitudeType.ML)
    evt = EventAssemblyService.create_event_from_cluster(
        Cluster("workspace1", "c123", ["p1"], t, loc),
        loc, mag, []
    )
    print(f"Event: {evt.magnitude.value} {evt.magnitude.type.value} @ {evt.location.latitude},{evt.location.longitude}")
    print(f"  Hash: {EventAssemblyService.event_hash(evt)}")
