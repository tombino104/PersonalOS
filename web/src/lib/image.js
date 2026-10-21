export const PHOTO_SIZE = 512;

export function coverSquare(width, height) {
  const side = Math.min(width, height);
  return { x: Math.floor((width - side) / 2), y: Math.floor((height - side) / 2), side };
}

export async function resizePhoto(file, size = PHOTO_SIZE) {
  const bitmap = await createImageBitmap(file);
  const { x, y, side } = coverSquare(bitmap.width, bitmap.height);
  const target = Math.min(size, side);
  const canvas = document.createElement('canvas');
  canvas.width = target;
  canvas.height = target;
  canvas.getContext('2d').drawImage(bitmap, x, y, side, side, 0, 0, target, target);
  bitmap.close?.();
  const encode = (type, quality) => new Promise((resolve) => canvas.toBlob(resolve, type, quality));
  const webp = await encode('image/webp', 0.85);
  if (webp && webp.type === 'image/webp') return webp;
  return encode('image/jpeg', 0.88);
}
