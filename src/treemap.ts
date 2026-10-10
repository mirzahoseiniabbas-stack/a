export interface MapNode {
  id: string;
  label: string;
  value: number;
  children?: MapNode[];
}

export function treemap<T extends MapNode>(items: T[]): Array<T & { x: number; y: number; w: number; h: number }> {
  const rects: Array<T & { x: number; y: number; w: number; h: number }> = [];
  const place = (nodes: T[], x: number, y: number, w: number, h: number) => {
    const usable = nodes.filter((node) => node.value > 0);
    const total = usable.reduce((sum, node) => sum + node.value, 0);
    if (!total || w <= 0 || h <= 0) return;
    let cursor = 0;
    const horizontal = w >= h;
    for (const node of usable) {
      const span = (node.value / total) * (horizontal ? w : h);
      const rx = horizontal ? x + cursor : x;
      const ry = horizontal ? y : y + cursor;
      const rw = horizontal ? span : w;
      const rh = horizontal ? h : span;
      cursor += span;
      if (node.children?.length) place(node.children as T[], rx, ry, rw, rh);
      else rects.push({ ...node, x: rx, y: ry, w: rw, h: rh });
    }
  };
  place(items, 0, 0, 100, 100);
  return rects;
}
