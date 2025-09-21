"""STL modification operations"""

import numpy as np
import trimesh
from typing import Tuple, Optional
from scipy.spatial import Delaunay


def fill_battery_gap(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """
    Completely fill the battery cover gap to create a solid continuous back plate.
    """
    vertices = mesh.vertices.copy()
    faces = mesh.faces.copy()
    
    # Find the bottom Z value (back of the case)
    z_min = vertices[:, 2].min()
    z_threshold = z_min + 0.5  # Vertices within 0.5mm of back
    
    # Get all vertices on the back plane
    back_vertices_mask = np.abs(vertices[:, 2] - z_min) < z_threshold
    back_vertex_indices = np.where(back_vertices_mask)[0]
    
    if len(back_vertex_indices) == 0:
        return mesh
    
    # Get the outer boundary of the back
    back_verts = vertices[back_vertex_indices]
    x_min, y_min = back_verts[:, :2].min(axis=0) 
    x_max, y_max = back_verts[:, :2].max(axis=0)
    
    # Create a grid of points to fill any gaps in the back plate
    grid_density = 2.0  # mm between points
    x_points = np.arange(x_min, x_max, grid_density)
    y_points = np.arange(y_min, y_max, grid_density)
    
    # Create new vertices for complete back plate
    new_vertices = []
    for x in x_points:
        for y in y_points:
            # Check if this point is inside the boundary
            # Simple rectangular boundary for now
            if x_min <= x <= x_max and y_min <= y <= y_max:
                new_vertices.append([x, y, z_min])
    
    if len(new_vertices) > 0:
        new_vertices = np.array(new_vertices)
        
        # Combine with existing back vertices
        all_back_points = np.vstack([back_verts, new_vertices])
        
        # Remove duplicates
        unique_points, unique_indices = np.unique(
            np.round(all_back_points, decimals=2), 
            axis=0, 
            return_index=True
        )
        
        # Triangulate the back plate
        if len(unique_points) > 3:
            points_2d = unique_points[:, :2]
            tri = Delaunay(points_2d)
            
            # Add new vertices to mesh
            vertex_offset = len(vertices)
            vertices = np.vstack([vertices, unique_points])
            
            # Add new faces
            new_faces = tri.simplices + vertex_offset
            faces = np.vstack([faces, new_faces])
    
    # Create new mesh
    filled_mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    
    # Remove duplicate and degenerate faces
    filled_mesh.merge_vertices()
    filled_mesh.remove_degenerate_faces()
    filled_mesh.remove_duplicate_faces()
    filled_mesh.remove_unreferenced_vertices()
    
    return filled_mesh


def add_magsafe_recess(mesh: trimesh.Trimesh, 
                       outer_radius: float = 28.0,
                       inner_radius: float = 22.5,
                       depth: float = 2.5,
                       position: Optional[Tuple[float, float]] = None) -> trimesh.Trimesh:
    """
    Add a circular MagSafe ring recess into the back plate (recessed inward from back).
    The recess is carved INTO the case from the back side.
    """
    vertices = mesh.vertices.copy()
    faces = mesh.faces.copy()
    
    # Determine position for the recess
    bounds = mesh.bounds
    if position is None:
        # Center it on the back plate
        center_x = (bounds[0][0] + bounds[1][0]) / 2
        center_y = (bounds[0][1] + bounds[1][1]) / 2
    else:
        center_x, center_y = position
    
    # Find the bottom Z value (back of the case)
    z_min = vertices[:, 2].min()
    
    # Create the ring recess by moving vertices INWARD (positive Z direction)
    # Find vertices on the back within the ring area
    distances_from_center = np.sqrt(
        (vertices[:, 0] - center_x)**2 + 
        (vertices[:, 1] - center_y)**2
    )
    
    # Vertices on the back surface that are within the outer ring radius
    back_surface_mask = np.abs(vertices[:, 2] - z_min) < 0.5
    
    # Different regions of the recess
    # 1. Inner circle (full depth) - this is where the ring sits
    inner_circle_mask = (distances_from_center <= inner_radius) & back_surface_mask
    
    # 2. Ring area (full depth) - between inner and outer radius
    ring_area_mask = (
        (distances_from_center > inner_radius) & 
        (distances_from_center <= outer_radius) & 
        back_surface_mask
    )
    
    # Move vertices in ring area up (into the case) to create recess
    vertices[ring_area_mask, 2] += depth
    
    # The inner circle stays at original level (creates the center platform)
    # No change needed for inner_circle_mask vertices
    
    # Now create the walls of the recess
    num_segments = 64
    angles = np.linspace(0, 2*np.pi, num_segments, endpoint=False)
    
    new_vertices = []
    new_faces = []
    
    # Outer wall of recess
    for i, angle in enumerate(angles):
        x = center_x + outer_radius * np.cos(angle)
        y = center_y + outer_radius * np.sin(angle)
        
        # Bottom and top of outer wall
        new_vertices.append([x, y, z_min])  # Bottom (back surface)
        new_vertices.append([x, y, z_min + depth])  # Top (recessed)
    
    # Inner wall of recess
    for i, angle in enumerate(angles):
        x = center_x + inner_radius * np.cos(angle)
        y = center_y + inner_radius * np.sin(angle)
        
        # Bottom and top of inner wall
        new_vertices.append([x, y, z_min])  # Bottom (back surface)
        new_vertices.append([x, y, z_min + depth])  # Top (recessed)
    
    # Add new vertices to mesh
    if len(new_vertices) > 0:
        vertex_offset = len(vertices)
        new_vertices = np.array(new_vertices)
        vertices = np.vstack([vertices, new_vertices])
        
        # Create faces for walls
        for i in range(num_segments):
            next_i = (i + 1) % num_segments
            
            # Outer wall faces
            v1 = vertex_offset + 2*i
            v2 = vertex_offset + 2*i + 1
            v3 = vertex_offset + 2*next_i + 1
            v4 = vertex_offset + 2*next_i
            
            new_faces.extend([
                [v1, v2, v3],
                [v1, v3, v4]
            ])
            
            # Inner wall faces (reversed for correct normals)
            v1 = vertex_offset + 2*num_segments + 2*i
            v2 = vertex_offset + 2*num_segments + 2*i + 1
            v3 = vertex_offset + 2*num_segments + 2*next_i + 1
            v4 = vertex_offset + 2*num_segments + 2*next_i
            
            new_faces.extend([
                [v1, v4, v3],
                [v1, v3, v2]
            ])
        
        if len(new_faces) > 0:
            new_faces = np.array(new_faces)
            faces = np.vstack([faces, new_faces])
    
    # Create new mesh
    modified_mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    
    # Clean up
    modified_mesh.merge_vertices()
    modified_mesh.remove_degenerate_faces()
    modified_mesh.remove_duplicate_faces()
    modified_mesh.remove_unreferenced_vertices()
    modified_mesh.fix_normals()
    
    return modified_mesh


def apply_modifications(mesh: trimesh.Trimesh, 
                       remove_battery_gap: bool = True,
                       add_magsafe: bool = True,
                       magsafe_position: Optional[Tuple[float, float]] = None) -> trimesh.Trimesh:
    """
    Apply all modifications to the mesh.
    """
    modified_mesh = mesh.copy()
    
    if remove_battery_gap:
        # Completely fill the battery gap to make solid back
        modified_mesh = fill_battery_gap(modified_mesh)
        print("Filled battery gap - back plate is now solid")
    
    if add_magsafe:
        # Add the magsafe recess (carved into the back)
        modified_mesh = add_magsafe_recess(
            modified_mesh,
            outer_radius=28.0,  # 56mm diameter
            inner_radius=22.5,  # 45mm diameter  
            depth=2.5,  # 2.5mm deep recess
            position=magsafe_position
        )
        print("Added MagSafe ring recess")
    
    # Final cleanup
    modified_mesh.fix_normals()
    
    # Verify we still have a flat back
    z_min = modified_mesh.vertices[:, 2].min()
    back_vertices = modified_mesh.vertices[
        np.abs(modified_mesh.vertices[:, 2] - z_min) < 0.1
    ]
    if len(back_vertices) > 0:
        print(f"Back plate Z range: {back_vertices[:, 2].min():.2f} to {back_vertices[:, 2].max():.2f}")
    
    return modified_mesh