#!/usr/bin/env python3
"""
LPIPS Perceptual Quality Calculator v1.0

Calculates Learned Perceptual Image Patch Similarity (LPIPS) between two images.
LPIPS correlates better with human perception than SSIM or MSE.

Requirements:
    pip install torch torchvision lpips pillow

Usage:
    python lpips-calculator.py <image1> <image2> [--output=json]
"""

import sys
import argparse
import json
from pathlib import Path

try:
    import torch
    import lpips
    from PIL import Image
    import torchvision.transforms as transforms
except ImportError as e:
    print(json.dumps({
        'error': 'Missing dependencies',
        'message': str(e),
        'install': 'pip install torch torchvision lpips pillow'
    }))
    sys.exit(1)


def load_image(image_path):
    """Load and preprocess image for LPIPS."""
    img = Image.open(image_path).convert('RGB')

    # LPIPS expects images in range [-1, 1]
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
    ])

    return transform(img).unsqueeze(0)


def calculate_lpips(image1_path, image2_path, use_gpu=False):
    """
    Calculate LPIPS distance between two images.

    Returns:
        dict: {
            'lpips_distance': float (0-1, lower is better),
            'similarity_percent': float (0-100, higher is better),
            'perceptual_quality': str (EXCELLENT/GOOD/FAIR/POOR)
        }
    """
    # Load LPIPS model (using AlexNet backbone by default)
    device = 'cuda' if use_gpu and torch.cuda.is_available() else 'cpu'
    loss_fn = lpips.LPIPS(net='alex').to(device)

    # Load images
    img1 = load_image(image1_path).to(device)
    img2 = load_image(image2_path).to(device)

    # Calculate LPIPS distance
    with torch.no_grad():
        distance = loss_fn(img1, img2).item()

    # Convert to similarity percentage (inverse, scaled to 0-100)
    # LPIPS typically ranges from 0 (identical) to ~1 (very different)
    # We'll use exponential scaling for better range
    similarity = 100 * (1 - min(distance, 1.0))

    # Classify perceptual quality
    if distance < 0.1:
        quality = 'EXCELLENT'
    elif distance < 0.3:
        quality = 'GOOD'
    elif distance < 0.6:
        quality = 'FAIR'
    else:
        quality = 'POOR'

    return {
        'lpips_distance': round(distance, 4),
        'similarity_percent': round(similarity, 2),
        'perceptual_quality': quality,
        'device': device
    }


def main():
    parser = argparse.ArgumentParser(description='Calculate LPIPS perceptual similarity')
    parser.add_argument('image1', help='Path to first image')
    parser.add_argument('image2', help='Path to second image')
    parser.add_argument('--output', choices=['json', 'text'], default='json',
                        help='Output format')
    parser.add_argument('--gpu', action='store_true',
                        help='Use GPU if available')

    args = parser.parse_args()

    # Validate image paths
    if not Path(args.image1).exists():
        print(json.dumps({'error': f'Image not found: {args.image1}'}))
        sys.exit(1)
    if not Path(args.image2).exists():
        print(json.dumps({'error': f'Image not found: {args.image2}'}))
        sys.exit(1)

    try:
        result = calculate_lpips(args.image1, args.image2, use_gpu=args.gpu)

        if args.output == 'json':
            print(json.dumps(result, indent=2))
        else:
            print(f"LPIPS Distance: {result['lpips_distance']:.4f}")
            print(f"Similarity: {result['similarity_percent']:.2f}%")
            print(f"Quality: {result['perceptual_quality']}")
            print(f"Device: {result['device']}")

    except Exception as e:
        print(json.dumps({
            'error': 'Calculation failed',
            'message': str(e)
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
