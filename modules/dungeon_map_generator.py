# dungeon_map_generator.py
import random
import math
import uuid
import logging
from .shared.output_writer import register_handler

# Define the dice types and their corresponding room types
DICE_TYPES = ['d4', 'd6', 'd8', 'd10', 'd12', 'd20']
DICE_ROOM_TYPES = {
    'd4': 'Small side room or larger corridor',
    'd6': 'Rectangular chamber',
    'd8': 'Irregularly-shaped chamber',
    'd10': 'Main objective or passage leading deeper',
    'd12': 'Special feature (river, chasm, tunnel)',
    'd20': 'Grand hall or important chamber'
}

def simulate_dice_drops(num_dice):
    # Ensure at least one d6 and one d10 are included
    dice_pool = ['d6', 'd10']
    # Fill the rest of the dice
    while len(dice_pool) < num_dice:
        dice_pool.append(random.choice(DICE_TYPES))

    # Initialize nodes list
    nodes = []
    # Simulate a 2D grid of size (e.g., 100x100 units)
    grid_size = 100
    for dice in dice_pool:
        x = random.uniform(0, grid_size)
        y = random.uniform(0, grid_size)
        node = {
            'id': str(uuid.uuid4()),
            'dice': dice,
            'room_type': DICE_ROOM_TYPES[dice],
            'position': (x, y)
        }
        nodes.append(node)
    return nodes


def combine_touching_nodes(nodes, threshold=10):
    combined = []
    while nodes:
        node = nodes.pop()
        to_merge = [node]
        for other in nodes[:]:
            distance = euclidean_distance(node['position'], other['position'])
            if distance < threshold:
                to_merge.append(other)
                nodes.remove(other)
        if len(to_merge) > 1:
            # Combine nodes into one larger node
            combined_node = merge_nodes(to_merge)
            combined.append(combined_node)
        else:
            combined.append(node)
    return combined

def euclidean_distance(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def merge_nodes(nodes):
    # Merge positions by averaging
    avg_x = sum(node['position'][0] for node in nodes) / len(nodes)
    avg_y = sum(node['position'][1] for node in nodes) / len(nodes)
    merged_node = {
        'id': str(uuid.uuid4()),
        'dice': max(nodes, key=lambda n: DICE_TYPES.index(n['dice']))['dice'],  # Use the largest dice type
        'room_type': DICE_ROOM_TYPES[max(nodes, key=lambda n: DICE_TYPES.index(n['dice']))['dice']],
        'position': (avg_x, avg_y),
        'sub_nodes': nodes  # Store the merged nodes
    }
    return merged_node


def create_loops(nodes):
    edges = []
    # Filter nodes by dice type for easy access
    node_dict = {dice: [node for node in nodes if node['dice'] == dice] for dice in DICE_TYPES}

    # Step-by-step connections based on dice types
    loop_sequence = ['d6', 'd8', 'd10', 'd12', 'd20']
    for i in range(len(loop_sequence) - 1):
        start_dice = loop_sequence[i]
        end_dice = loop_sequence[i + 1]
        for start_node in node_dict.get(start_dice, []):
            if node_dict.get(end_dice):
                end_node = find_closest_node(start_node, node_dict[end_dice])
                edge = (start_node['id'], end_node['id'])
                edges.append(edge)
            else:
                logging.warning(f"No node of type {end_dice} found to connect with {start_dice}")
    # Connect d20 back to d6 to complete the loop
    for d20_node in node_dict.get('d20', []):
        if node_dict.get('d6'):
            start_node = find_closest_node(d20_node, node_dict['d6'])
            edge = (d20_node['id'], start_node['id'])
            edges.append(edge)
        else:
            logging.warning("No d6 node found to connect back from d20")
    return edges


def connect_remaining_nodes(nodes, edges):
    connected_node_ids = set([node_id for edge in edges for node_id in edge])
    unconnected_nodes = [node for node in nodes if node['id'] not in connected_node_ids]
    for node in unconnected_nodes:
        closest_node = find_closest_node(node, nodes, exclude_ids=[node['id']])
        if closest_node:
            edge = (node['id'], closest_node['id'])
            edges.append(edge)
    return edges

def find_closest_node(node, nodes, exclude_ids=None):
    if exclude_ids is None:
        exclude_ids = []
    min_distance = float('inf')
    closest_node = None
    for other_node in nodes:
        if other_node['id'] in exclude_ids:
            continue
        distance = euclidean_distance(node['position'], other_node['position'])
        if distance < min_distance:
            min_distance = distance
            closest_node = other_node
    return closest_node


def identify_traversals_and_junctions(nodes, edges):
    traversals = []
    junctions = []
    # Check for traversals
    for node in nodes:
        node_id = node['id']
        node_pos = node['position']
        for edge in edges:
            if node_id not in edge:
                start_node = next(n for n in nodes if n['id'] == edge[0])
                end_node = next(n for n in nodes if n['id'] == edge[1])
                if line_intersects_circle(start_node['position'], end_node['position'], node_pos, radius=5):
                    traversals.append({'node_id': node_id, 'edge': edge})
    # Check for junctions
    for i in range(len(edges)):
        for j in range(i+1, len(edges)):
            edge1 = edges[i]
            edge2 = edges[j]
            if edges_cross(nodes, edge1, edge2):
                junctions.append({'edges': (edge1, edge2)})
    return traversals, junctions

def line_intersects_circle(p1, p2, center, radius):
    # Line segment from p1 to p2, circle centered at center with given radius
    # Check if the line intersects the circle
    # Implement the mathematical logic
    pass  # Implement this function

def edges_cross(nodes, edge1, edge2):
    # Check if two edges cross each other
    n1_start = next(n for n in nodes if n['id'] == edge1[0])
    n1_end = next(n for n in nodes if n['id'] == edge1[1])
    n2_start = next(n for n in nodes if n['id'] == edge2[0])
    n2_end = next(n for n in nodes if n['id'] == edge2[1])
    return lines_intersect(n1_start['position'], n1_end['position'], n2_start['position'], n2_end['position'])

def lines_intersect(a1, a2, b1, b2):
    # Implement line intersection logic
    pass  # Implement this function


def designate_entrance(nodes):
    # Choose the smallest dice size node (e.g., d4) or a random node
    smallest_dice_nodes = [node for node in nodes if node['dice'] == 'd4']
    if not smallest_dice_nodes:
        smallest_dice_nodes = nodes  # Fallback to any node
    entrance_node = random.choice(smallest_dice_nodes)
    entrance_node['is_entrance'] = True
    logging.info(f"🚪 Dungeon entrance designated at node ID: {entrance_node['id']}")
    return entrance_node


def key_elements(nodes, edges, traversals, junctions):
    # Key nodes
    for idx, node in enumerate(nodes, 1):
        node['key'] = f"Room {idx}"
    # Key junctions
    for idx, traversal in enumerate(traversals, 1):
        traversal['key'] = f"Traversal {idx}"
    for idx, junction in enumerate(junctions, 1):
        junction['key'] = f"Junction {idx}"
    return nodes, traversals, junctions


def generate_dungeon_map(num_dice):
    nodes = simulate_dice_drops(num_dice)
    nodes = combine_touching_nodes(nodes)
    edges = create_loops(nodes)
    edges = connect_remaining_nodes(nodes, edges)
    traversals, junctions = identify_traversals_and_junctions(nodes, edges)
    entrance = designate_entrance(nodes)
    nodes, traversals, junctions = key_elements(nodes, edges, traversals, junctions)
    dungeon_map = {
        'nodes': nodes,
        'edges': edges,
        'traversals': traversals,
        'junctions': junctions,
        'entrance': entrance
    }
    return dungeon_map


def dungeon_map_handler(data, f):
    f.write("## Dungeon Map\n\n")
    f.write("### Nodes (Rooms):\n\n")
    for node in data['dungeon_map']['nodes']:
        f.write(f"- **{node.get('key', node['id'])}**: {node['room_type']} at position {node['position']}\n")
        if node.get('is_entrance'):
            f.write("  - This is the entrance.\n")
    f.write("\n### Connections (Edges):\n\n")
    for edge in data['dungeon_map']['edges']:
        f.write(f"- {edge[0]} connected to {edge[1]}\n")
    if data['dungeon_map']['traversals']:
        f.write("\n### Traversals:\n\n")
        for traversal in data['dungeon_map']['traversals']:
            f.write(f"- **{traversal['key']}**: Node {traversal['node_id']} intersects edge {traversal['edge']}\n")
    if data['dungeon_map']['junctions']:
        f.write("\n### Junctions:\n\n")
        for junction in data['dungeon_map']['junctions']:
            f.write(f"- **{junction['key']}**: Edges {junction['edges'][0]} and {junction['edges'][1]} intersect\n")
    f.write("\n")

register_handler("dungeon_map", dungeon_map_handler)