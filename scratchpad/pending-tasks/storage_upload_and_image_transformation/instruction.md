Your application needs to display uniform user avatars, but users upload images in varying sizes and aspect ratios.

You need to write a client-side JavaScript snippet using the `appwrite` SDK that uploads a local image file to an Appwrite Storage bucket and subsequently generates a URL for a 200x200 pixel cropped preview.

**Constraints:**
- You MUST use the `storage.createFile()` method to handle the upload process.
- You MUST use the `storage.getFilePreview()` API with the appropriate width and height parameters to generate the thumbnail URL.