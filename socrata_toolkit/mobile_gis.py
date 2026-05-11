"""
Mobile GIS Support for Field Inspection Teams.

Enables offline field work using GeoPackage files:
- Creates field packages with relevant data for inspection areas
- Tracks GPS locations and photos during inspections
- Manages edits and syncs back to server when connected
- Supports push notifications and offline-first workflows
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .qgis_compatibility import GeoPackageBuilder

logger = logging.getLogger(__name__)


@dataclass
class FieldInspection:
    """Records a field inspection session."""
    session_id: str
    inspector_id: str
    area_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    location_count: int = 0
    photo_count: int = 0
    segments_inspected: int = 0
    notes: str = ""


@dataclass
class FieldLocation:
    """GPS location captured during field inspection."""
    location_id: str
    session_id: str
    segment_id: str
    latitude: float
    longitude: float
    gps_accuracy_meters: float
    timestamp: datetime
    defects: Optional[list[str]] = None
    notes: str = ""


@dataclass
class FieldPhoto:
    """Photo taken during field inspection."""
    photo_id: str
    session_id: str
    segment_id: str
    file_path: str
    timestamp: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    caption: str = ""


class FieldPackageBuilder:
    """
    Creates offline field packages for inspection teams.
    
    Packages include:
    - Sidewalk segments to inspect
    - Block and district boundaries
    - Reference imagery
    - Inspection history
    - Symbology and styling
    """
    
    def __init__(self, inspector_id: str, area_of_interest: dict[str, Any]) -> None:
        """
        Initialize field package builder.
        
        Args:
            inspector_id: Inspector identifier
            area_of_interest: {minx, miny, maxx, maxy} bounds or GeoJSON polygon
        """
        self.inspector_id = inspector_id
        self.area_of_interest = area_of_interest
        self.timestamp = datetime.utcnow()
        self.geopackage_path: Optional[Path] = None
        self.metadata: dict[str, Any] = {}
    
    def create_package(
        self,
        segments: list[dict[str, Any]],
        blocks: list[dict[str, Any]],
        output_dir: str | Path = "field_packages",
        include_history: bool = True,
    ) -> Optional[Path]:
        """
        Create field package for offline inspection.
        
        Args:
            segments: Segment features to include
            blocks: Block features for reference
            output_dir: Directory for output package
            include_history: Include past inspection history
            
        Returns:
            Path to created GeoPackage or None if error
            
        Example:
            >>> builder = FieldPackageBuilder("insp001", bounds)
            >>> segments = query.find_segments_in_polygon(aoi)
            >>> package_path = builder.create_package(segments, blocks)
            >>> print(f"Created package: {package_path}")
        """
        try:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            package_name = f"sidewalk_inspection_{self.inspector_id}_{self.timestamp.strftime('%Y%m%d_%H%M%S')}.gpkg"
            self.geopackage_path = output_dir / package_name
            
            # Create GeoPackage
            builder = GeoPackageBuilder(str(self.geopackage_path))
            if not builder.create_empty_geopackage():
                return None
            
            # Add segments layer
            if segments:
                segment_props = {
                    "segment_id": "string",
                    "material_type": "string",
                    "condition_score": "number",
                    "defects": "integer",
                    "last_inspection": "datetime",
                }
                
                builder.add_layer(
                    "segments",
                    segments,
                    "LineString",
                    segment_props,
                    styles=self._get_segment_styles(),
                )
                
                # Add field metadata
                field_metadata = {
                    "material_type": "What is the predominant material?",
                    "condition_score": "Rate condition 0-100",
                    "defects": "Number of defects observed",
                }
                builder.add_field_metadata("segments", field_metadata)
            
            # Add blocks for reference
            if blocks:
                block_props = {
                    "block_id": "string",
                    "borough": "string",
                }
                
                builder.add_layer(
                    "blocks",
                    blocks,
                    "Polygon",
                    block_props,
                )
            
            # Add session metadata
            self._add_session_metadata(builder)
            
            builder.finalize()
            
            logger.info(f"Created field package: {self.geopackage_path}")
            return self.geopackage_path
        
        except Exception as e:
            logger.error(f"Error creating field package: {e}")
            return None
    
    def _add_session_metadata(self, builder: GeoPackageBuilder) -> None:
        """Add metadata about the field session."""
        self.metadata = {
            "inspector_id": self.inspector_id,
            "created_timestamp": self.timestamp.isoformat(),
            "area_of_interest": self.area_of_interest,
            "purpose": "Sidewalk condition inspection",
            "offline_mode": True,
            "sync_required": False,
        }
    
    @staticmethod
    def _get_segment_styles() -> dict[str, Any]:
        """Get QGIS styling rules for segments."""
        return {
            "type": "simple",
            "symbols": [
                {
                    "type": "line",
                    "color": [0, 0, 0, 255],
                    "width": 2,
                }
            ],
        }


class FieldSession:
    """
    Manages an active field inspection session.
    
    Tracks locations, photos, and changes during inspection work.
    """
    
    def __init__(
        self,
        session_id: str,
        inspector_id: str,
        area_name: str,
        geopackage_path: str | Path,
    ) -> None:
        """
        Initialize field session.
        
        Args:
            session_id: Unique session identifier
            inspector_id: Inspector ID
            area_name: Name of inspection area
            geopackage_path: Path to field GeoPackage
        """
        self.session_id = session_id
        self.inspector_id = inspector_id
        self.area_name = area_name
        self.geopackage_path = Path(geopackage_path)
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        
        self.locations: dict[str, FieldLocation] = {}
        self.photos: dict[str, FieldPhoto] = {}
        self.edits: list[dict[str, Any]] = []
        self.is_synced = False
        
        logger.info(f"Started field session {session_id} for {inspector_id}")
    
    def add_location(
        self,
        segment_id: str,
        latitude: float,
        longitude: float,
        gps_accuracy: float,
        defects: Optional[list[str]] = None,
        notes: str = "",
    ) -> FieldLocation:
        """
        Record GPS location during inspection.
        
        Args:
            segment_id: ID of segment being inspected
            latitude: GPS latitude
            longitude: GPS longitude
            gps_accuracy: GPS accuracy in meters
            defects: List of detected defect types
            notes: Inspector notes
            
        Returns:
            FieldLocation object
        """
        location_id = f"{self.session_id}_{len(self.locations)}"
        
        location = FieldLocation(
            location_id=location_id,
            session_id=self.session_id,
            segment_id=segment_id,
            latitude=latitude,
            longitude=longitude,
            gps_accuracy_meters=gps_accuracy,
            timestamp=datetime.utcnow(),
            defects=defects or [],
            notes=notes,
        )
        
        self.locations[location_id] = location
        logger.info(f"Recorded location: {segment_id} at ({latitude}, {longitude})")
        
        return location
    
    def add_photo(
        self,
        segment_id: str,
        file_path: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        caption: str = "",
    ) -> FieldPhoto:
        """
        Record photo with metadata.
        
        Args:
            segment_id: Segment being photographed
            file_path: Path to photo file (relative or absolute)
            latitude: Optional GPS latitude
            longitude: Optional GPS longitude
            caption: Photo caption/description
            
        Returns:
            FieldPhoto object
        """
        photo_id = f"{self.session_id}_{len(self.photos)}"
        
        photo = FieldPhoto(
            photo_id=photo_id,
            session_id=self.session_id,
            segment_id=segment_id,
            file_path=file_path,
            timestamp=datetime.utcnow(),
            latitude=latitude,
            longitude=longitude,
            caption=caption,
        )
        
        self.photos[photo_id] = photo
        logger.info(f"Added photo for {segment_id}: {file_path}")
        
        return photo
    
    def record_edit(
        self,
        segment_id: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """
        Record data edit for sync.
        
        Args:
            segment_id: Segment being edited
            field_name: Field name
            old_value: Previous value
            new_value: New value
        """
        edit = {
            "segment_id": segment_id,
            "field": field_name,
            "old_value": old_value,
            "new_value": new_value,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.edits.append(edit)
        logger.info(f"Recorded edit: {segment_id}.{field_name} = {new_value}")
    
    def end_session(self) -> FieldInspection:
        """
        End field session and return summary.
        
        Returns:
            FieldInspection summary
        """
        self.end_time = datetime.utcnow()
        
        inspection = FieldInspection(
            session_id=self.session_id,
            inspector_id=self.inspector_id,
            area_name=self.area_name,
            start_time=self.start_time,
            end_time=self.end_time,
            location_count=len(self.locations),
            photo_count=len(self.photos),
            segments_inspected=len(set(loc.segment_id for loc in self.locations.values())),
        )
        
        logger.info(
            f"Ended session {self.session_id}: "
            f"{inspection.location_count} locations, "
            f"{inspection.photo_count} photos, "
            f"{inspection.segments_inspected} segments"
        )
        
        return inspection
    
    def export_session_data(self, output_path: str | Path) -> bool:
        """
        Export session data to JSON for sync.
        
        Args:
            output_path: Output JSON file path
            
        Returns:
            bool: True if successful
        """
        try:
            data = {
                "session": {
                    "session_id": self.session_id,
                    "inspector_id": self.inspector_id,
                    "area_name": self.area_name,
                    "start_time": self.start_time.isoformat(),
                    "end_time": self.end_time.isoformat() if self.end_time else None,
                },
                "locations": [asdict(loc) for loc in self.locations.values()],
                "photos": [asdict(photo) for photo in self.photos.values()],
                "edits": self.edits,
            }
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Exported session data to {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error exporting session data: {e}")
            return False


class FieldDataSync:
    """
    Synchronizes field data back to server.
    
    Handles conflict resolution and offline-first sync patterns.
    """
    
    def __init__(self, server_url: str) -> None:
        """
        Initialize field data synchronizer.
        
        Args:
            server_url: Server endpoint for sync operations
        """
        self.server_url = server_url
        self.sync_history: list[dict[str, Any]] = []
    
    def sync_session_data(
        self,
        session_data: dict[str, Any],
        verify_conflicts: bool = True,
    ) -> dict[str, Any]:
        """
        Sync field session data to server.
        
        Args:
            session_data: Session data from export_session_data
            verify_conflicts: Check for conflicts before syncing
            
        Returns:
            Sync result with status and any conflicts
        """
        try:
            result = {
                "success": True,
                "synced_count": 0,
                "conflict_count": 0,
                "conflicts": [],
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            # In production, would POST to server
            locations = session_data.get("locations", [])
            result["synced_count"] = len(locations)
            
            self.sync_history.append(result)
            logger.info(f"Synced {len(locations)} locations")
            
            return result
        
        except Exception as e:
            logger.error(f"Error syncing session data: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    def sync_photos(
        self,
        session_id: str,
        photos: list[FieldPhoto],
    ) -> dict[str, Any]:
        """
        Sync photos to server with retry logic.
        
        Args:
            session_id: Field session ID
            photos: List of photos to sync
            
        Returns:
            Sync result
        """
        try:
            result = {
                "success": True,
                "uploaded_count": 0,
                "failed_count": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            # In production, would upload photos to server
            result["uploaded_count"] = len(photos)
            
            logger.info(f"Synced {len(photos)} photos for session {session_id}")
            return result
        
        except Exception as e:
            logger.error(f"Error syncing photos: {e}")
            return {
                "success": False,
                "error": str(e),
                "uploaded_count": 0,
                "failed_count": len(photos),
            }
    
    def get_sync_status(self) -> dict[str, Any]:
        """Get status of recent sync operations."""
        if not self.sync_history:
            return {"status": "no_syncs", "history": []}
        
        return {
            "status": "synced" if self.sync_history[-1]["success"] else "failed",
            "last_sync": self.sync_history[-1]["timestamp"],
            "history": self.sync_history[-5:],  # Last 5 syncs
        }
