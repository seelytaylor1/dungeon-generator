import random
import uuid
import logging
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Constants
PAPER_WIDTH = 8.5  # Standard US letter width
PAPER_HEIGHT = 11  # Standard US letter height
GRID_WIDTH = 17  # Double the paper width, rounded to integer
GRID_HEIGHT = 22  # Double the paper height, rounded to integer
GRID_CELLS = GRID_WIDTH * GRID_HEIGHT

@dataclass
class GridCell:
    uid: str
    x: int
    y: int
    occupied: bool = False
    room_id: Optional[str] = None

@dataclass
class Room:
    id: str
    position: Tuple[int, int]
    room_type: str
    connections: List[str] = None
    is_entrance: bool = False
    is_terminus: bool = False
    loop_color: Optional[str] = None

@dataclass
class Connection:
    start_id: str
    end_id: str
    type: str = "path"  # path, junction, or crossing

class DungeonGridManager:
    def __init__(self):
        self.grid = self._initialize_grid()
        self.rooms: List[Room] = []
        self.connections: List[Connection] = []
        
    def _initialize_grid(self) -> List[List[GridCell]]:
        """Create a 16x22 grid of cells."""
        grid = []
        for y in range(GRID_HEIGHT):
            row = []
            for x in range(GRID_WIDTH):
                cell = GridCell(
                    uid=str(uuid.uuid4()),
                    x=x,
                    y=y
                )
                row.append(cell)
            grid.append(row)
        return grid

    def place_rooms(self, count: int = 15):
        """Place specified number of rooms randomly on the grid."""
        for _ in range(count):
            while True:
                x = random.randint(1, GRID_WIDTH-2)
                y = random.randint(1, GRID_HEIGHT-2)
                if not self.grid[y][x].occupied:
                    room = Room(
                        id=str(uuid.uuid4()),
                        position=(x, y),
                        room_type="chamber"
                    )
                    self.rooms.append(room)
                    self._mark_cell_occupied(x, y, room.id)
                    break

    def designate_special_rooms(self):
        """Randomly designate entrance and terminus rooms."""
        available_rooms = [r for r in self.rooms]
        
        # Select entrance
        entrance = random.choice(available_rooms)
        entrance.room_type = "entrance"
        entrance.is_entrance = True
        available_rooms.remove(entrance)
        
        # Select terminus
        terminus = random.choice(available_rooms)
        terminus.room_type = "terminus"
        terminus.is_terminus = True

    def connect_path_to_terminus(self):
        """Create a path from entrance to terminus."""
        entrance = next(r for r in self.rooms if r.is_entrance)
        terminus = next(r for r in self.rooms if r.is_terminus)
        current = entrance
        visited = {current.id}
        
        while current.id != terminus.id:
            # Find unvisited room closest to terminus
            unvisited = [r for r in self.rooms if r.id not in visited]
            if not unvisited:
                break
                
            next_room = min(unvisited, 
                key=lambda r: self._manhattan_distance(r.position, terminus.position))
            
            self.connections.append(Connection(current.id, next_room.id))
            current = next_room
            visited.add(current.id)

    def connect_rooms_to_entrance(self):
        """Connect unconnected rooms back to entrance."""
        entrance = next(r for r in self.rooms if r.is_entrance)
        connected = {c.start_id for c in self.connections} | {c.end_id for c in self.connections}
        
        for room in self.rooms:
            if room.id not in connected:
                self.connections.append(Connection(room.id, entrance.id))

    def connect_remaining_rooms(self):
        """Connect any remaining unconnected rooms to nearest neighbors."""
        connected = {c.start_id for c in self.connections} | {c.end_id for c in self.connections}
        
        for room in self.rooms:
            if room.id not in connected:
                other_rooms = [r for r in self.rooms if r.id != room.id]
                nearest = min(other_rooms,
                    key=lambda r: self._manhattan_distance(r.position, room.position))
                self.connections.append(Connection(room.id, nearest.id))

    def detect_junctions_and_crossings(self):
        """Detect where paths overlap or cross through rooms."""
        # Convert connections to line segments for intersection checking
        segments = []
        for conn in self.connections:
            start_room = next(r for r in self.rooms if r.id == conn.start_id)
            end_room = next(r for r in self.rooms if r.id == conn.end_id)
            segments.append((
                start_room.position,
                end_room.position,
                conn
            ))

        # Check all pairs of segments for intersections
        for i, (start1, end1, conn1) in enumerate(segments):
            for j, (start2, end2, conn2) in enumerate(segments[i+1:], i+1):
                if self._segments_intersect(start1, end1, start2, end2):
                    intersection_point = self._get_intersection_point(
                        start1, end1, start2, end2
                    )
                    
                    # Check if intersection is at a room
                    intersected_room = self._find_room_at_point(intersection_point)
                    
                    if intersected_room:
                        # Mark as crossing if intersection is at a room
                        conn1.type = "crossing"
                        conn2.type = "crossing"
                        logger.debug(f"Crossing detected at room {intersected_room.id}")
                    else:
                        # Mark as junction if intersection is between rooms
                        conn1.type = "junction"
                        conn2.type = "junction"
                        logger.debug(f"Junction detected at {intersection_point}")

    def generate_map_content(self) -> Dict[str, Any]:
        """Generate map content for documentation."""
        content = {
            "rooms": [],
            "connections": [],
            "junctions": [],
            "crossings": []
        }
        
        # Process rooms
        for i, room in enumerate(self.rooms, 1):
            room_data = {
                "id": room.id,
                "number": i,
                "type": room.room_type,
                "position": room.position,
                "is_entrance": room.is_entrance,
                "is_terminus": room.is_terminus,
                "loop_color": room.loop_color
            }
            content["rooms"].append(room_data)
            
        # Add ALL connections to the connections list
        for conn in self.connections:
            conn_data = {
                "start": conn.start_id,
                "end": conn.end_id,
                "type": conn.type
            }
            content["connections"].append(conn_data)
            
            # Also add to specific type lists if applicable
            if conn.type == "junction":
                content["junctions"].append(conn_data)
            elif conn.type == "crossing":
                content["crossings"].append(conn_data)
                
        return content

    def save_map_visualization(self, filename: str = "docs/dungeon_map.png"):
        """Generate and save the map visualization."""
        plt.figure(figsize=(PAPER_WIDTH, PAPER_HEIGHT), dpi=300)  # Use paper dimensions
        
        # Create networkx graph
        G = nx.Graph()
        pos = {}
        node_colors = []
        
        # Add nodes (rooms)
        for room in self.rooms:
            G.add_node(room.id)
            pos[room.id] = room.position
            
            # Determine node color
            if room.is_entrance:
                color = '#90EE90'  # Light green
            elif room.is_terminus:
                color = '#FFB6C1'  # Pink
            elif room.loop_color == 'red':
                color = '#FF9999'  # Red
            elif room.loop_color == 'blue':
                color = '#99CCFF'  # Blue
            else:
                color = '#F0F0F0'  # Gray
            node_colors.append(color)
        
        # Add edges (connections)
        edge_colors = []
        for conn in self.connections:
            G.add_edge(conn.start_id, conn.end_id)
            if conn.type == "junction":
                edge_colors.append('orange')
            elif conn.type == "crossing":
                edge_colors.append('purple')
            else:
                edge_colors.append('gray')
        
        # Draw the graph with larger nodes and text
        nx.draw_networkx_nodes(G, pos, 
            node_color=node_colors, 
            node_size=500,  # Increased from 200
            edgecolors='black', 
            linewidths=1.0  # Increased from 0.5
        )
        nx.draw_networkx_edges(G, pos, 
            edge_color=edge_colors, 
            width=1.5,  # Increased from 1
            alpha=0.7
        )
        nx.draw_networkx_labels(G, pos, 
            {room.id: str(i+1) for i, room in enumerate(self.rooms)},
            font_size=8,  # Increased from 6
            font_family='sans-serif',
            font_weight='bold'  # Added bold
        )
        
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.title("Dungeon Map", fontsize=8)
        plt.axis('off')
        plt.tight_layout(pad=0.3)
        plt.savefig(filename, bbox_inches='tight')
        plt.close()

    # Helper methods
    def _mark_cell_occupied(self, x: int, y: int, room_id: str):
        """Mark a grid cell as occupied by a room."""
        self.grid[y][x].occupied = True
        self.grid[y][x].room_id = room_id

    def _manhattan_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
        """Calculate Manhattan distance between two points."""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def _segments_intersect(self, start1, end1, start2, end2) -> bool:
        """Check if two line segments intersect."""
        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
        
        return (ccw(start1, start2, end2) != ccw(end1, start2, end2) and 
                ccw(start1, end1, start2) != ccw(start1, end1, end2))

    def _get_intersection_point(self, start1, end1, start2, end2) -> Tuple[int, int]:
        """Calculate the intersection point of two line segments."""
        # Simple approximation - average of midpoints
        mid1 = ((start1[0] + end1[0])//2, (start1[1] + end1[1])//2)
        mid2 = ((start2[0] + end2[0])//2, (start2[1] + end2[1])//2)
        return ((mid1[0] + mid2[0])//2, (mid1[1] + mid2[1])//2)

    def _find_room_at_point(self, point: Tuple[int, int]) -> Optional[Room]:
        """Find if there's a room at the given point."""
        x, y = point
        if 0 <= y < GRID_HEIGHT and 0 <= x < GRID_WIDTH:
            cell = self.grid[y][x]
            if cell.occupied:
                return next((r for r in self.rooms if r.id == cell.room_id), None)
        return None

    def _get_room_number(self, room_id: str) -> int:
        """Helper method to get room number from room ID."""
        for i, room in enumerate(self.rooms, 1):
            if room.id == room_id:
                return i
        return 0  # Return 0 if room not found

    def create_loop(self, color: str, center_x: int, center_y: int):
        """Create a 5-room loop around a center point."""
        loop_rooms = []
        angles = [0, 72, 144, 216, 288]  # 360/5 degrees spacing
        radius = 3  # Distance from center
        
        for angle in angles:
            while True:
                # Convert polar to grid coordinates
                rad = math.radians(angle)
                x = int(center_x + radius * math.cos(rad))
                y = int(center_y + radius * math.sin(rad))
                
                # Ensure within bounds
                x = max(1, min(x, GRID_WIDTH-2))
                y = max(1, min(y, GRID_HEIGHT-2))
                
                if not self.grid[y][x].occupied:
                    room = Room(
                        id=str(uuid.uuid4()),
                        position=(x, y),
                        room_type="chamber",
                        loop_color=color
                    )
                    loop_rooms.append(room)
                    self._mark_cell_occupied(x, y, room.id)
                    break
        
        # Connect rooms in loop
        for i in range(len(loop_rooms)):
            start = loop_rooms[i]
            end = loop_rooms[(i + 1) % len(loop_rooms)]
            self.connections.append(Connection(start.id, end.id))
        
        self.rooms.extend(loop_rooms)
        return loop_rooms

    def place_special_rooms(self):
        """Place entrance and terminus rooms."""
        # Place entrance near bottom
        entrance_y = GRID_HEIGHT - 4
        entrance_x = int(GRID_WIDTH/4)
        
        # Place terminus near top
        terminus_y = 4
        terminus_x = int(3*GRID_WIDTH/4)
        
        entrance = Room(
            id=str(uuid.uuid4()),
            position=(entrance_x, entrance_y),
            room_type="entrance",
            is_entrance=True
        )
        
        terminus = Room(
            id=str(uuid.uuid4()),
            position=(terminus_x, terminus_y),
            room_type="terminus",
            is_terminus=True
        )
        
        self.rooms.extend([entrance, terminus])
        self._mark_cell_occupied(entrance_x, entrance_y, entrance.id)
        self._mark_cell_occupied(terminus_x, terminus_y, terminus.id)
        return entrance, terminus

    def add_loose_rooms(self, count: int = 2):
        """Add loose rooms - one connects loops, one connects to nearest neighbor."""
        # First loose room connects between loops
        red_rooms = [r for r in self.rooms if r.loop_color == 'red']
        blue_rooms = [r for r in self.rooms if r.loop_color == 'blue']
        
        # Find centers of loops
        red_center = (sum(r.position[0] for r in red_rooms)/5, 
                     sum(r.position[1] for r in red_rooms)/5)
        blue_center = (sum(r.position[0] for r in blue_rooms)/5,
                      sum(r.position[1] for r in blue_rooms)/5)
        
        # Place first room between loops
        mid_x = int((red_center[0] + blue_center[0])/2)
        mid_y = int((red_center[1] + blue_center[1])/2)
        
        # Add some randomness to the midpoint
        mid_x += random.randint(-2, 2)
        mid_y += random.randint(-2, 2)
        
        if not self.grid[mid_y][mid_x].occupied:
            connector_room = Room(
                id=str(uuid.uuid4()),
                position=(mid_x, mid_y),
                room_type="loose_chamber"
            )
            self._mark_cell_occupied(mid_x, mid_y, connector_room.id)
            
            # Connect to closest room in each loop
            red_nearest = min(red_rooms,
                key=lambda r: self._manhattan_distance(r.position, connector_room.position))
            blue_nearest = min(blue_rooms,
                key=lambda r: self._manhattan_distance(r.position, connector_room.position))
            
            self.connections.append(Connection(connector_room.id, red_nearest.id))
            self.connections.append(Connection(connector_room.id, blue_nearest.id))
            self.rooms.append(connector_room)
        
        # Second loose room connects to nearest neighbor
        while True:
            x = random.randint(1, GRID_WIDTH-2)
            y = random.randint(1, GRID_HEIGHT-2)
            if not self.grid[y][x].occupied:
                room = Room(
                    id=str(uuid.uuid4()),
                    position=(x, y),
                    room_type="loose_chamber"
                )
                self._mark_cell_occupied(x, y, room.id)
                
                # Find nearest room
                other_rooms = [r for r in self.rooms if r.id != room.id]
                nearest = min(other_rooms,
                    key=lambda r: self._manhattan_distance(r.position, room.position))
                
                self.connections.append(Connection(room.id, nearest.id))
                self.rooms.append(room)
                break

def generate_dungeon_map(*args, **kwargs) -> Dict[str, Any]:
    """Main generation function."""
    try:
        logger.info("🗺️ Starting dungeon map generation...")
        
        dungeon = DungeonGridManager()
        
        # Create red loop in bottom left quadrant
        red_loop = dungeon.create_loop('red', int(GRID_WIDTH/4), int(3*GRID_HEIGHT/4))
        
        # Create blue loop in top right quadrant
        blue_loop = dungeon.create_loop('blue', int(3*GRID_WIDTH/4), int(GRID_HEIGHT/4))
        
        # Add entrance and terminus
        entrance, terminus = dungeon.place_special_rooms()
        
        # Connect entrance to red loop and terminus to blue loop
        red_room = min(red_loop, key=lambda r: dungeon._manhattan_distance(r.position, entrance.position))
        blue_room = min(blue_loop, key=lambda r: dungeon._manhattan_distance(r.position, terminus.position))
        dungeon.connections.append(Connection(entrance.id, red_room.id))
        dungeon.connections.append(Connection(terminus.id, blue_room.id))
        
        # Add loose rooms
        dungeon.add_loose_rooms(2)
        
        dungeon.detect_junctions_and_crossings()
        
        # Generate content and visualization
        content = dungeon.generate_map_content()
        dungeon.save_map_visualization()

        # Create nodes list for dungeon content generator
        nodes = []
        for i, room in enumerate(dungeon.rooms, 1):
            nodes.append({
                "key": f"Room {i}",
                "room_type": room.room_type,
                "position": room.position,
                "is_entrance": room.is_entrance,
                "is_terminus": room.is_terminus,
                "loop_color": room.loop_color
            })
        
        # Format for documentation
        doc_content = (
            "## Dungeon Map\n\n"
            "### Rooms\n" +
            "\n".join(f"- Room {r['number']}: {r['type']}" 
                     for r in content['rooms']) +
            "\n\n### Connections\n" +
            "\n".join(f"- Room {dungeon._get_room_number(c['start'])} to Room {dungeon._get_room_number(c['end'])}"
                     for c in content['connections']) +
            "\n\n### Junctions\n" +
            "\n".join(f"- Junction between paths Room {dungeon._get_room_number(j['start'])} - Room {dungeon._get_room_number(j['end'])}"
                     for j in content['junctions']) +
            "\n\n### Crossings\n" +
            "\n".join(f"- Crossing at Room {dungeon._get_room_number(c['start'])} with path to Room {dungeon._get_room_number(c['end'])}"
                     for c in content['crossings']) +
            "\n\n![Dungeon Map](./dungeon_map.png)"
        )
        
        # Write to documentation
        from utils.doc_writer import DocumentationBuilder
        doc_builder = DocumentationBuilder()
        doc_builder.write_section("dungeon_map", doc_content)
        
        return {
            "content": doc_content,
            "metadata": {
                "nodes": nodes,  # Add nodes list to metadata
                "connections": content['connections'],
                "junctions": content['junctions'],
                "crossings": content['crossings']
            }
        }
        
    except Exception as e:
        logger.error(f"Dungeon map generation failed: {str(e)}")
        return {"error": str(e)}