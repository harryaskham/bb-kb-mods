"""Hole detection and analysis for STL meshes"""

import numpy as np
import trimesh
from typing import List, Dict, Tuple


def detect_holes_simple(mesh: trimesh.Trimesh) -> int:
    """
    Simple hole count using trimesh's built-in methods.
    """
    # Get the outline of the mesh
    try:
        # Get boundary edges
        outline = mesh.outline()
        if outline is not None:
            # Each separate path is a hole
            entities = outline.entities
            return len(entities)
    except:
        pass
    
    # Fallback: count based on Euler characteristic
    # For a mesh with h holes: V - E + F = 2 - 2h
    # So h = (2 - V + E - F) / 2
    if hasattr(mesh, 'euler_number'):
        euler = mesh.euler_number
        # For a surface with holes, euler = 2 - 2*g - b where g is genus and b is boundary components
        # Assuming genus 0 (no handles), holes = (2 - euler) / 2
        holes = max(0, (2 - euler) // 2)
        return holes
    
    return -1  # Unknown


def verify_hole_count(mesh: trimesh.Trimesh, expected_count: int = 7) -> Tuple[bool, str]:
    """
    Simplified hole verification.
    """
    hole_count = detect_holes_simple(mesh)
    
    if hole_count == -1:
        return False, "Could not detect holes in mesh"
    
    message = f"Detected approximately {hole_count} holes/boundaries\n"
    
    if hole_count == expected_count:
        message += f"✓ Matches expected count of {expected_count}"
        return True, message
    else:
        message += f"⚠ Expected {expected_count} holes"
        return False, message