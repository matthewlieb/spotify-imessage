// Simple script to generate PWA icons
// Run with: node generate-icons.js

const fs = require('fs');

// Minimal valid PNG (1x1 transparent pixel) - we'll create proper icons
function createMinimalPNG() {
  // This is a minimal valid PNG file (1x1 transparent)
  // We'll replace this with proper icon generation
  return Buffer.from([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, // PNG signature
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52, // IHDR chunk
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, // 1x1 dimensions
    0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
    0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
    0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
    0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
    0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
    0x42, 0x60, 0x82
  ]);
}

// Try to use canvas if available, otherwise create simple colored squares
try {
  const { createCanvas } = require('canvas');
  
  function createIcon(size, filename) {
    const canvas = createCanvas(size, size);
    const ctx = canvas.getContext('2d');
    
    // Spotify green background
    ctx.fillStyle = '#1db954';
    ctx.fillRect(0, 0, size, size);
    
    // Dark circle
    ctx.fillStyle = '#0f172a';
    const padding = size * 0.1;
    ctx.beginPath();
    ctx.arc(size/2, size/2, (size/2) - padding, 0, 2 * Math.PI);
    ctx.fill();
    
    // Music note symbol
    ctx.fillStyle = '#1db954';
    ctx.font = `${size * 0.4}px Arial`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('♪', size/2, size/2);
    
    const buffer = canvas.toBuffer('image/png');
    fs.writeFileSync(filename, buffer);
    console.log(`Created ${filename} (${size}x${size})`);
  }
  
  createIcon(192, 'icon-192.png');
  createIcon(512, 'icon-512.png');
  console.log('Icons generated successfully!');
  
} catch (e) {
  console.log('Canvas package not available. Creating simple placeholder icons...');
  console.log('To generate proper icons, either:');
  console.log('1. Install canvas: npm install canvas');
  console.log('2. Or open create-icons.html in your browser and download the icons');
  
  // Create simple colored square PNGs as placeholders
  // For now, let's use a different approach - create SVG and convert, or use ImageMagick
  console.log('\nCreating minimal valid PNG files...');
  fs.writeFileSync('icon-192.png', createMinimalPNG());
  fs.writeFileSync('icon-512.png', createMinimalPNG());
  console.log('Created placeholder icons. Please regenerate using create-icons.html in your browser.');
}
