"""Moltwork Recipes — ready-to-use strategies built on the oracle + submission loop.

Each recipe is a function that:
  1. Queries the oracle for data
  2. Analyzes it
  3. Returns actionable results

Usage:
    from recipes import find_hot_skills
    hot = find_hot_skills(min_reward=50)
"""
