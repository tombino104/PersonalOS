const path = (d) => ({ tag: 'path', attrs: { d } });
const dot = (cx) => ({ tag: 'circle', attrs: { cx, cy: 12, r: 1.2, fill: 'currentColor', stroke: 'none' } });

export const icons = {
  home: [path('M4 11.5 12 5l8 6.5V19a1 1 0 0 1-1 1h-4v-5H9v5H5a1 1 0 0 1-1-1z')],
  star: [path('M12 3.5 19.5 8v8L12 20.5 4.5 16V8z'), path('M12 3.5v17M4.5 8l15 8M19.5 8l-15 8')],
  pencil: [path('M4.5 19.5 5.5 15 16 4.5a2.1 2.1 0 0 1 3 3L8.5 18z'), path('m14 6.5 3 3')],
  more: [dot(6), dot(12), dot(18)],
  back: [path('m14.5 6-6 6 6 6')],
  forward: [path('m9.5 6 6 6-6 6')],
  archive: [path('M4 8h16v11a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1zM3 4.5h18V8H3zM10 12.5h4')],
  sliders: [
    path('M4 7h8M18 7h2M4 17h2M12 17h8'),
    { tag: 'circle', attrs: { cx: 15, cy: 7, r: 2.5 } },
    { tag: 'circle', attrs: { cx: 9, cy: 17, r: 2.5 } },
  ],
  chart: [path('M5 19.5V11M12 19.5V5M19 19.5v-6')],
  up: [path('m6 14.5 6-6 6 6')],
  down: [path('m6 9.5 6 6 6-6')],
  check: [path('m5 12.5 4.5 4.5L19 7.5')],
  smile: [
    { tag: 'circle', attrs: { cx: 12, cy: 12, r: 8.5 } },
    path('M8.5 14.2c1 1.4 2.2 2 3.5 2s2.5-.6 3.5-2'),
    { tag: 'circle', attrs: { cx: 9.3, cy: 9.8, r: 0.6, fill: 'currentColor' } },
    { tag: 'circle', attrs: { cx: 14.7, cy: 9.8, r: 0.6, fill: 'currentColor' } },
  ],
  tree: [
    { tag: 'circle', attrs: { cx: 12, cy: 5.5, r: 2.2 } },
    { tag: 'circle', attrs: { cx: 6, cy: 18, r: 2.2 } },
    { tag: 'circle', attrs: { cx: 18, cy: 18, r: 2.2 } },
    path('M12 7.7v3.3M12 11l-5 5M12 11l5 5'),
  ],
  calendar: [
    { tag: 'rect', attrs: { x: 4, y: 5, width: 16, height: 15, rx: 2 } },
    path('M4 10h16M9 3v4M15 3v4'),
  ],
  book: [path('M5 5.5a2 2 0 0 1 2-2h11v14H7a2 2 0 0 0-2 2z'), path('M5 19.5a2 2 0 0 0 2 2h11v-4')],
  heart: [path('M12 20s-7.5-4.6-7.5-10.2A4.1 4.1 0 0 1 12 7.6a4.1 4.1 0 0 1 7.5 2.2C19.5 15.4 12 20 12 20z')],
  bell: [path('M6 16v-5a6 6 0 1 1 12 0v5l1.5 2h-15z'), path('M10 20a2 2 0 0 0 4 0')],
  plug: [path('M9 3v5M15 3v5M7 8h10v3a5 5 0 0 1-10 0z'), path('M12 16v5')],
};
