# Slice the prepared transparent atlas without rescaling its pixel artwork.
# Run from any folder: powershell -File path/to/split_sprites.ps1
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$atlasPath = Join-Path $PSScriptRoot 'sprites_atlas.png'
$outputPath = Join-Path $PSScriptRoot 'sprites'
[System.IO.Directory]::CreateDirectory($outputPath) | Out-Null
$atlas = [System.Drawing.Bitmap]::new($atlasPath)

# Rectangles use the original 1536x1024 layout: left, top, width, height.
$regions = [ordered]@{
    sandwich = @(25, 155, 175, 200)
    tomato = @(205, 155, 155, 200)
    noodles = @(365, 155, 170, 200)
    milk = @(545, 150, 140, 205)
    box_sandwich = @(725, 145, 200, 275)
    box_tomato = @(925, 145, 190, 275)
    box_noodles = @(1115, 145, 195, 275)
    box_milk = @(1310, 145, 210, 275)
    plate = @(60, 550, 490, 330)
    pot_empty = @(620, 545, 280, 275)
    pot_cooking = @(915, 545, 280, 275)
    pot_cooked = @(1205, 545, 295, 275)
}

$manifest = [ordered]@{}
try {
    if ($atlas.Width -ne 1536 -or $atlas.Height -ne 1024) {
        throw 'Expected a 1536x1024 atlas. Inspect layout before changing slice regions.'
    }
    foreach ($entry in $regions.GetEnumerator()) {
        $region = $entry.Value
        $rectangle = [System.Drawing.Rectangle]::new($region[0], $region[1], $region[2], $region[3])
        $crop = $atlas.Clone($rectangle, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        try {
            $left = $crop.Width
            $top = $crop.Height
            $right = -1
            $bottom = -1
            for ($y = 0; $y -lt $crop.Height; $y++) {
                for ($x = 0; $x -lt $crop.Width; $x++) {
                    $pixel = $crop.GetPixel($x, $y)
                    # Remove faint generation halos and keep crisp sprite edges.
                    if ($pixel.A -ge 128) {
                        $crop.SetPixel($x, $y, [System.Drawing.Color]::FromArgb(255, $pixel.R, $pixel.G, $pixel.B))
                        $left = [Math]::Min($left, $x)
                        $top = [Math]::Min($top, $y)
                        $right = [Math]::Max($right, $x)
                        $bottom = [Math]::Max($bottom, $y)
                    } else {
                        $crop.SetPixel($x, $y, [System.Drawing.Color]::Transparent)
                    }
                }
            }
            if ($right -lt 0) { throw "No artwork found for $($entry.Key)" }
            # Keep two transparent pixels around each trimmed sprite.
            $width = $right - $left + 1
            $height = $bottom - $top + 1
            $sprite = [System.Drawing.Bitmap]::new($width + 4, $height + 4)
            $graphics = [System.Drawing.Graphics]::FromImage($sprite)
            try {
                $graphics.Clear([System.Drawing.Color]::Transparent)
                $source = [System.Drawing.Rectangle]::new($left, $top, $width, $height)
                $destination = [System.Drawing.Rectangle]::new(2, 2, $width, $height)
                $graphics.DrawImage($crop, $destination, $source, [System.Drawing.GraphicsUnit]::Pixel)
                $fileName = "$($entry.Key).png"
                $sprite.Save((Join-Path $outputPath $fileName), [System.Drawing.Imaging.ImageFormat]::Png)
                $manifest[$entry.Key] = [ordered]@{
                    file = "sprites/$fileName"
                    width = $sprite.Width
                    height = $sprite.Height
                    atlas_region = $region
                }
            } finally {
                $graphics.Dispose()
                $sprite.Dispose()
            }
        } finally { $crop.Dispose() }
    }
    $manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'sprites.json') -Encoding UTF8
    Write-Output "Exported $($manifest.Count) transparent sprites to $outputPath"
} finally { $atlas.Dispose() }
