"""D3.js and d3blocks-powered visualization components for NYC DOT SIM Division.

Renders rich HTML strings containing embedded D3 v7 charts. In Dash, embed via
``dash_dangerously_set_inner_html`` or a ``dcc.Iframe`` with a ``srcDoc``. In
Streamlit, use ``st.components.v1.html(html_str, height=N, scrolling=True)``.

Included chart types (all self-contained single-file HTML):
- chord_diagram        — borough↔violation-type relationship matrix
- force_network        — inspection-to-permit proximity network
- treemap_d3           — nested borough/community-board violation hierarchy
- packed_circles       — bubble hierarchy for violation density
- stream_graph         — area-stream of violation types over time
- hex_binmap           — hex-bin spatial density map (lat/lon)

All functions return ``str`` (raw HTML with inline D3 v7 CDN, no build step).

Dependencies: none beyond a browser; all D3 loaded from unpkg CDN.

Example::

    from socrata_toolkit.viz.d3_components import chord_diagram, force_network

    html = chord_diagram(matrix, groups=["MN", "BX", "BK", "QN", "SI"])
    with open("chord.html", "w") as f:
        f.write(html)
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd


_D3_CDN = "https://unpkg.com/d3@7/dist/d3.min.js"

_HTML_WRAPPER = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ margin: 0; font-family: 'Segoe UI', Arial, sans-serif; background: #f8f9fa; }}
    svg {{ display: block; margin: auto; }}
    .tooltip {{
      position: absolute;
      background: rgba(0,0,0,0.75);
      color: #fff;
      padding: 6px 10px;
      border-radius: 4px;
      font-size: 12px;
      pointer-events: none;
      opacity: 0;
    }}
  </style>
</head>
<body>
  <div id="container"></div>
  <div class="tooltip" id="tooltip"></div>
  <script src="{d3cdn}"></script>
  <script>
    {script}
  </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Chord Diagram
# ---------------------------------------------------------------------------

def chord_diagram(
    matrix: list[list[float]],
    groups: list[str],
    colors: list[str] | None = None,
    width: int = 600,
    title: str = "Chord Diagram",
) -> str:
    """D3 chord diagram showing pairwise flow magnitude.

    Args:
        matrix: Square NxN matrix of flow values (e.g. inspection cross-counts).
        groups: N group labels (e.g. borough names or violation types).
        colors: N hex color strings; defaults to DOT palette.
        width: SVG width in pixels (height = width).
        title: Chart title injected as SVG text.

    Returns:
        Self-contained HTML string.
    """
    colors = colors or [
        "#003366", "#D63384", "#198754", "#FD7E14",
        "#6610F2", "#0D6EFD", "#20C997", "#FFC107",
    ]
    script = f"""
const width = {width}, height = {width};
const outerRadius = Math.min(width, height) * 0.5 - 60;
const innerRadius = outerRadius - 24;

const matrix = {json.dumps(matrix)};
const names  = {json.dumps(groups)};
const colors = {json.dumps(colors[:len(groups)])};

const color = d3.scaleOrdinal(names, colors);
const chord  = d3.chord().padAngle(0.04).sortSubgroups(d3.descending)(matrix);
const arc    = d3.arc().innerRadius(innerRadius).outerRadius(outerRadius);
const ribbon = d3.ribbon().radius(innerRadius - 1).padAngle(1/innerRadius);

const svg = d3.select("#container").append("svg")
    .attr("width", width).attr("height", height + 30)
    .append("g")
    .attr("transform", `translate(${{width/2}},${{height/2 + 30}})`);

svg.append("text")
    .attr("y", -outerRadius - 20)
    .attr("text-anchor", "middle")
    .style("font-size", "14px").style("font-weight", "bold")
    .text("{title}");

const group = svg.append("g").selectAll("g").data(chord.groups).join("g");

group.append("path")
    .attr("d", arc)
    .attr("fill", d => color(names[d.index]))
    .attr("stroke", "#fff")
    .on("mouseover", (ev, d) => {{
        d3.select("#tooltip").style("opacity",1)
          .html(`<b>${{names[d.index]}}</b><br>Total: ${{d3.format(",.0f")(d.value)}}`);
    }})
    .on("mousemove", ev => d3.select("#tooltip").style("left", ev.pageX+10+"px").style("top", ev.pageY-20+"px"))
    .on("mouseout",  () => d3.select("#tooltip").style("opacity",0));

group.append("text")
    .each(d => {{ d.angle = (d.startAngle + d.endAngle) / 2; }})
    .attr("dy", ".35em")
    .attr("transform", d =>
        `rotate(${{(d.angle * 180 / Math.PI - 90)}}) translate(${{outerRadius + 8}}) ${{d.angle > Math.PI ? "rotate(180)" : ""}}`)
    .attr("text-anchor", d => d.angle > Math.PI ? "end" : null)
    .style("font-size", "11px")
    .text(d => names[d.index]);

svg.append("g").attr("fill-opacity", 0.67)
    .selectAll("path").data(chord).join("path")
    .attr("d", ribbon)
    .attr("fill", d => color(names[d.target.index]))
    .attr("stroke", d => d3.rgb(color(names[d.target.index])).darker())
    .on("mouseover", (ev, d) => {{
        d3.select("#tooltip").style("opacity",1)
          .html(`${{names[d.source.index]}} → ${{names[d.target.index]}}: ${{d3.format(",.0f")(d.source.value)}}`);
    }})
    .on("mousemove", ev => d3.select("#tooltip").style("left", ev.pageX+10+"px").style("top", ev.pageY-20+"px"))
    .on("mouseout",  () => d3.select("#tooltip").style("opacity",0));
"""
    return _HTML_WRAPPER.format(d3cdn=_D3_CDN, script=script)


# ---------------------------------------------------------------------------
# Force-directed Network
# ---------------------------------------------------------------------------

def force_network(
    nodes: list[dict],
    links: list[dict],
    width: int = 720,
    height: int = 520,
    title: str = "Network",
) -> str:
    """D3 force-directed graph.

    Args:
        nodes: List of dicts with ``id`` (str) and optional ``group`` (str), ``value`` (float).
        links: List of dicts with ``source`` (node id), ``target`` (node id), ``value`` (float).
        width, height: SVG dimensions in pixels.
        title: Chart title.

    Returns:
        Self-contained HTML string.
    """
    script = f"""
const width = {width}, height = {height};
const nodes = {json.dumps(nodes)};
const links = {json.dumps(links)};
const groups = [...new Set(nodes.map(d => d.group || "default"))];
const color = d3.scaleOrdinal(groups,
    ["#003366","#D63384","#198754","#FD7E14","#6610F2","#0D6EFD","#20C997","#FFC107"]);

const svg = d3.select("#container").append("svg")
    .attr("width", width).attr("height", height + 24);

svg.append("text").attr("x", width/2).attr("y", 18)
    .attr("text-anchor","middle").style("font-size","13px").style("font-weight","bold")
    .text("{title}");

const g = svg.append("g").attr("transform","translate(0,24)");

const sim = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(60))
    .force("charge", d3.forceManyBody().strength(-120))
    .force("center", d3.forceCenter(width/2, height/2))
    .force("collision", d3.forceCollide(18));

const link = g.append("g").attr("stroke","#aaa").attr("stroke-opacity",0.5)
    .selectAll("line").data(links).join("line")
    .attr("stroke-width", d => Math.sqrt(d.value || 1));

const node = g.append("g").selectAll("circle").data(nodes).join("circle")
    .attr("r", d => 5 + Math.sqrt(d.value || 1) * 2)
    .attr("fill", d => color(d.group || "default"))
    .attr("stroke","#fff").attr("stroke-width",1.5)
    .call(d3.drag()
        .on("start", (ev,d) => {{ if (!ev.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; }})
        .on("drag",  (ev,d) => {{ d.fx=ev.x; d.fy=ev.y; }})
        .on("end",   (ev,d) => {{ if (!ev.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }}))
    .on("mouseover", (ev,d) => {{
        d3.select("#tooltip").style("opacity",1).html(`<b>${{d.id}}</b>${{d.group ? "<br>"+d.group : ""}}`);
    }})
    .on("mousemove", ev => d3.select("#tooltip").style("left",ev.pageX+10+"px").style("top",ev.pageY-20+"px"))
    .on("mouseout",  () => d3.select("#tooltip").style("opacity",0));

const label = g.append("g").selectAll("text").data(nodes).join("text")
    .text(d => d.id).style("font-size","10px").attr("dx",8).attr("dy","0.35em");

sim.on("tick", () => {{
    link.attr("x1",d=>d.source.x).attr("y1",d=>d.source.y)
        .attr("x2",d=>d.target.x).attr("y2",d=>d.target.y);
    node.attr("cx",d=>d.x).attr("cy",d=>d.y);
    label.attr("x",d=>d.x).attr("y",d=>d.y);
}});
"""
    return _HTML_WRAPPER.format(d3cdn=_D3_CDN, script=script)


# ---------------------------------------------------------------------------
# D3 Treemap
# ---------------------------------------------------------------------------

def treemap_d3(
    hierarchy_data: dict,
    width: int = 800,
    height: int = 500,
    title: str = "Treemap",
) -> str:
    """D3 treemap for hierarchical violation data.

    Args:
        hierarchy_data: Nested dict in D3 hierarchy format::

            {"name": "root", "children": [
                {"name": "MANHATTAN", "children": [
                    {"name": "CB101", "value": 340},
                    ...
                ]},
                ...
            ]}

        width, height: SVG dimensions.
        title: Chart title.

    Returns:
        Self-contained HTML string.
    """
    script = f"""
const width = {width}, height = {height};
const data = {json.dumps(hierarchy_data)};

const color = d3.scaleOrdinal(d3.schemeTableau10);

const hierarchy = d3.hierarchy(data)
    .sum(d => d.value || 0)
    .sort((a,b) => b.value - a.value);

d3.treemap().size([width, height]).padding(2).round(true)(hierarchy);

const svg = d3.select("#container").append("svg")
    .attr("width", width).attr("height", height + 28);

svg.append("text").attr("x", width/2).attr("y",18)
    .attr("text-anchor","middle").style("font-size","13px").style("font-weight","bold")
    .text("{title}");

const g = svg.append("g").attr("transform","translate(0,28)");

const leaf = g.selectAll("g").data(hierarchy.leaves()).join("g")
    .attr("transform", d => `translate(${{d.x0}},${{d.y0}})`);

leaf.append("rect")
    .attr("width",  d => d.x1 - d.x0)
    .attr("height", d => d.y1 - d.y0)
    .attr("fill", d => {{ let n = d; while (n.depth > 1) n = n.parent; return color(n.data.name); }})
    .attr("opacity", 0.82)
    .attr("stroke","#fff")
    .on("mouseover",(ev,d) => {{
        d3.select("#tooltip").style("opacity",1)
          .html(`<b>${{d.data.name}}</b><br>Value: ${{d3.format(",.0f")(d.value)}}`);
    }})
    .on("mousemove", ev => d3.select("#tooltip").style("left",ev.pageX+10+"px").style("top",ev.pageY-20+"px"))
    .on("mouseout",  () => d3.select("#tooltip").style("opacity",0));

leaf.append("text")
    .attr("x",4).attr("y",14)
    .style("font-size","10px").style("fill","white").style("pointer-events","none")
    .text(d => (d.x1-d.x0) > 40 ? d.data.name : "");
"""
    return _HTML_WRAPPER.format(d3cdn=_D3_CDN, script=script)


# ---------------------------------------------------------------------------
# Stream Graph
# ---------------------------------------------------------------------------

def stream_graph(
    df: pd.DataFrame,
    date_col: str,
    category_col: str,
    value_col: str,
    width: int = 800,
    height: int = 420,
    title: str = "Stream Graph",
) -> str:
    """D3 stream graph of category values over time.

    Args:
        df: Source DataFrame.
        date_col: Temporal column (parsed to YYYY-MM-DD strings).
        category_col: Category column (stacked series).
        value_col: Numeric metric.
        width, height: SVG dimensions.
        title: Chart title.

    Returns:
        Self-contained HTML string.
    """
    tmp = df.copy()
    tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce").dt.strftime("%Y-%m-%d")
    pivot = (
        tmp.groupby([date_col, category_col])[value_col]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    dates = pivot[date_col].tolist()
    categories = [c for c in pivot.columns if c != date_col]
    series_data = [{"key": cat, "values": pivot[cat].tolist()} for cat in categories]

    script = f"""
const width = {width}, height = {height};
const dates = {json.dumps(dates)};
const series = {json.dumps(series_data)};
const keys = series.map(d => d.key);

const color = d3.scaleOrdinal(keys,
    ["#003366","#D63384","#198754","#FD7E14","#6610F2","#0D6EFD","#20C997","#FFC107","#DC3545","#17A2B8"]);

const stackData = dates.map((date, i) => {{
    const obj = {{date}};
    series.forEach(s => obj[s.key] = s.values[i] || 0);
    return obj;
}});

const stack = d3.stack().keys(keys).offset(d3.stackOffsetWiggle)(stackData);
const xScale = d3.scalePoint().domain(dates).range([50, width-20]);
const yExtent = [d3.min(stack, l=>d3.min(l, d=>d[0])), d3.max(stack, l=>d3.max(l, d=>d[1]))];
const yScale = d3.scaleLinear().domain(yExtent).range([height-20, 20]);

const area = d3.area()
    .x((d, i) => xScale(dates[i]))
    .y0(d => yScale(d[0]))
    .y1(d => yScale(d[1]))
    .curve(d3.curveCatmullRom);

const svg = d3.select("#container").append("svg")
    .attr("width", width).attr("height", height + 30);

svg.append("text").attr("x",width/2).attr("y",16)
    .attr("text-anchor","middle").style("font-size","13px").style("font-weight","bold")
    .text("{title}");

const g = svg.append("g").attr("transform","translate(0,20)");

g.selectAll("path").data(stack).join("path")
    .attr("d", area)
    .attr("fill", d => color(d.key))
    .attr("opacity", 0.75)
    .on("mouseover",(ev,d) => {{
        d3.select("#tooltip").style("opacity",1).html(`<b>${{d.key}}</b>`);
    }})
    .on("mousemove", ev => d3.select("#tooltip").style("left",ev.pageX+10+"px").style("top",ev.pageY-20+"px"))
    .on("mouseout",  () => d3.select("#tooltip").style("opacity",0));

g.append("g").attr("transform",`translate(0,${{height-20}})`)
    .call(d3.axisBottom(xScale).tickValues(dates.filter((_,i)=>i%Math.ceil(dates.length/8)===0)));
"""
    return _HTML_WRAPPER.format(d3cdn=_D3_CDN, script=script)


# ---------------------------------------------------------------------------
# Hex-bin Density Map
# ---------------------------------------------------------------------------

def hex_binmap(
    df: pd.DataFrame,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    width: int = 760,
    height: int = 500,
    title: str = "Hex-Bin Density Map",
    radius: int = 12,
) -> str:
    """D3 hex-bin density map for lat/lon point data.

    Projects NYC coordinates to a simple equirectangular projection centred on
    NYC for a fast, dependency-free overview of spatial density.

    Args:
        df: Source DataFrame with latitude and longitude columns.
        lat_col, lon_col: Column names.
        width, height: SVG dimensions.
        title: Chart title.
        radius: Hex bin radius in pixels.

    Returns:
        Self-contained HTML string.
    """
    tmp = df[[lat_col, lon_col]].dropna().copy()
    tmp = tmp[(tmp[lat_col].between(40.47, 40.93)) & (tmp[lon_col].between(-74.26, -73.70))]
    pts = tmp[[lon_col, lat_col]].values.tolist()

    script = f"""
const width = {width}, height = {height};
const points = {json.dumps(pts)};
const radius = {radius};

// Simple equirectangular projection centred on NYC
const proj = d3.geoEquirectangular()
    .center([-73.98, 40.71])
    .scale(80000)
    .translate([width/2, height/2]);

const hexbin = d3.hexbin().extent([[0,0],[width,height]]).radius(radius);
const projected = points.map(p => proj(p));
const bins = hexbin(projected);
const maxBin = d3.max(bins, d => d.length) || 1;
const color = d3.scaleSequential([0, maxBin], d3.interpolateOrRd);

const svg = d3.select("#container").append("svg")
    .attr("width",width).attr("height",height+26);

svg.append("text").attr("x",width/2).attr("y",16)
    .attr("text-anchor","middle").style("font-size","13px").style("font-weight","bold")
    .text("{title}");

const g = svg.append("g").attr("transform","translate(0,22)");

g.selectAll("path").data(bins).join("path")
    .attr("d", hexbin.hexagon())
    .attr("transform", d=>`translate(${{d.x}},${{d.y}})`)
    .attr("fill", d => color(d.length))
    .attr("stroke","#fff").attr("stroke-width",0.4)
    .on("mouseover",(ev,d)=>{{
        d3.select("#tooltip").style("opacity",1).html(`Count: <b>${{d.length}}</b>`);
    }})
    .on("mousemove", ev=>d3.select("#tooltip").style("left",ev.pageX+10+"px").style("top",ev.pageY-20+"px"))
    .on("mouseout", ()=>d3.select("#tooltip").style("opacity",0));
"""
    # hex-bin needs d3-hexbin extension
    hexbin_cdn = "https://unpkg.com/d3-hexbin@0.2.2/build/d3-hexbin.min.js"
    wrapper = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ margin:0; font-family:'Segoe UI',Arial,sans-serif; background:#1a1a2e; color:#fff; }}
    svg {{ display:block; margin:auto; }}
    .tooltip {{ position:absolute; background:rgba(0,0,0,.75); color:#fff;
                padding:5px 9px; border-radius:4px; font-size:12px; pointer-events:none; opacity:0; }}
  </style>
</head>
<body>
  <div id="container"></div>
  <div class="tooltip" id="tooltip"></div>
  <script src="{d3cdn}"></script>
  <script src="{hexbin}"></script>
  <script>{script}</script>
</body>
</html>"""
    return wrapper.format(d3cdn=_D3_CDN, hexbin=hexbin_cdn, script=script)


# ---------------------------------------------------------------------------
# Helper: DataFrame → D3 Hierarchy
# ---------------------------------------------------------------------------

def df_to_hierarchy(
    df: pd.DataFrame,
    level_cols: list[str],
    value_col: str,
    agg: str = "sum",
) -> dict:
    """Convert a flat DataFrame into a nested D3 hierarchy dict.

    Args:
        df: Source DataFrame.
        level_cols: Ordered list of grouping columns (outer → inner),
            e.g. ["borough", "community_board", "status"].
        value_col: Numeric column for leaf values.
        agg: Aggregation function.

    Returns:
        Nested dict suitable for ``treemap_d3`` or ``packed_circles``.
    """

    def _recurse(sub: pd.DataFrame, levels: list[str]) -> list[dict]:
        if not levels:
            return []
        col = levels[0]
        children = []
        for val, group in sub.groupby(col):
            if len(levels) == 1:
                children.append({
                    "name": str(val),
                    "value": float(getattr(group[value_col], agg)()),
                })
            else:
                children.append({
                    "name": str(val),
                    "children": _recurse(group, levels[1:]),
                })
        return children

    return {"name": "root", "children": _recurse(df, level_cols)}
