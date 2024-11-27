---
title: Location-Based Replication
description: Geographic-aware data replication system
---

# Location-Based Replication

## Overview

The location-based replication system ensures data is distributed efficiently based on geographic coordinates and client proximity.

## Implementation

### Priority Calculation
```python
def calculate_server_score(distance: float, space_available: int):
    normalized_distance = distance / MAX_DISTANCE
    space_score = 1 - (space_available / total_space)
    return (DISTANCE_WEIGHT * normalized_distance + 
            SPACE_WEIGHT * space_score)
```

### Visualization

![Network Graph](/images/network-graph.png)
*Network visualization showing chunk servers (red) and clients (blue)*

## Features
1. Distance-based server selection
2. Space-aware distribution
3. Dynamic priority updates
4. Real-time visualization 