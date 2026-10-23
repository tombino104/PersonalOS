import { describe, expect, it } from 'vitest';
import { keyBytes } from './reminder.js';

describe('keyBytes', () => {
  it('decodes a url-safe base64 key without padding', () => {
    expect(Array.from(keyBytes('AQID'))).toEqual([1, 2, 3]);
    expect(Array.from(keyBytes('-_8'))).toEqual([251, 255]);
  });
});
