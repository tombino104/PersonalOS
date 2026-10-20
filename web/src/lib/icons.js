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
  check: [path('m5 12.5 4.5 4.5L19 7.5')],
};
