
# Design

## Achieving Parity

### Positioning

An important part of parity is sanely positioning nodes as people would want to, the same way a code formatter makes people
forget about syntactical positioning.

#### Flow

Graph flow is horizontal right-going in blender.

#### Trees formatting

All nodes will be laid out horizontally with identical (adjustable via pragma?) vertical and horizontal distances,
with minimal intersecting links.
All groups will be laid out in the same fashion as nodes using external links.
A separate file can be generated for people wanting to preserve original node positions.

#### Orphan nodes as comments

<!-- I suppose I need screenshots... -->

Often times people will leave orphan nodes as alternative paths through the graph as a form of
comment that they had tried or will try that instead.

They are often vertically aligned since the flow of the graph is horizontal.

Detecting this is difficult, probably as a start, will use a weighted vertical symmetry check
and place the orphan code as a comment above.

The above solution is somewhat unaligned with achieving parity but more aligned with semantic intent.
