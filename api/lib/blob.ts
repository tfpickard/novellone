/**
 * Vercel Blob Storage
 *
 * Handles cover image uploads and management using Vercel Blob storage.
 */

import { put, del, list, head } from '@vercel/blob';

// ───────────────────────────────────────────────────────────────────────────
// Upload Cover Image
// ───────────────────────────────────────────────────────────────────────────

/**
 * Upload a cover image to Vercel Blob storage.
 *
 * @param storyId - Story ID (used for filename)
 * @param imageUrl - Temporary DALL-E image URL to download and upload
 * @returns Public URL of the uploaded image
 */
export async function uploadCoverImage(
  storyId: string,
  imageUrl: string
): Promise<string> {
  // Download the DALL-E image
  const response = await fetch(imageUrl);
  if (!response.ok) {
    throw new Error(`Failed to download image: ${response.statusText}`);
  }

  const blob = await response.blob();

  // Upload to Vercel Blob with public access
  const { url } = await put(`covers/${storyId}.png`, blob, {
    access: 'public',
    addRandomSuffix: false, // Use exact filename for consistency
    contentType: 'image/png',
  });

  return url;
}

/**
 * Upload a cover image from a Buffer.
 *
 * @param storyId - Story ID
 * @param buffer - Image data as Buffer
 * @param contentType - Image MIME type
 * @returns Public URL of the uploaded image
 */
export async function uploadCoverImageFromBuffer(
  storyId: string,
  buffer: Buffer,
  contentType: string = 'image/png'
): Promise<string> {
  const { url } = await put(`covers/${storyId}.png`, buffer, {
    access: 'public',
    addRandomSuffix: false,
    contentType,
  });

  return url;
}

// ───────────────────────────────────────────────────────────────────────────
// Delete Cover Image
// ───────────────────────────────────────────────────────────────────────────

/**
 * Delete a cover image from Vercel Blob storage.
 *
 * @param url - Public URL of the image to delete
 */
export async function deleteCoverImage(url: string): Promise<void> {
  await del(url);
}

// ───────────────────────────────────────────────────────────────────────────
// List Cover Images
// ───────────────────────────────────────────────────────────────────────────

/**
 * List all cover images in storage.
 *
 * @returns Array of blob URLs
 */
export async function listCoverImages(): Promise<string[]> {
  const { blobs } = await list({ prefix: 'covers/' });
  return blobs.map((blob) => blob.url);
}

// ───────────────────────────────────────────────────────────────────────────
// Check if Cover Exists
// ───────────────────────────────────────────────────────────────────────────

/**
 * Check if a cover image exists for a story.
 *
 * @param storyId - Story ID
 * @returns True if the cover exists, false otherwise
 */
export async function coverImageExists(storyId: string): Promise<boolean> {
  try {
    // Construct expected URL (this depends on your Vercel Blob configuration)
    const expectedPath = `covers/${storyId}.png`;
    const { blobs } = await list({ prefix: expectedPath, limit: 1 });
    return blobs.length > 0;
  } catch {
    return false;
  }
}

// ───────────────────────────────────────────────────────────────────────────
// Get Cover Image Metadata
// ───────────────────────────────────────────────────────────────────────────

/**
 * Get metadata for a cover image.
 *
 * @param url - Public URL of the image
 * @returns Image metadata (size, content type, uploaded date)
 */
export async function getCoverImageMetadata(url: string): Promise<{
  size: number;
  contentType: string;
  uploadedAt: Date;
} | null> {
  try {
    const metadata = await head(url);
    return {
      size: metadata.size,
      contentType: metadata.contentType,
      uploadedAt: metadata.uploadedAt,
    };
  } catch {
    return null;
  }
}
