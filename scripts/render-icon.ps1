$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path $PSScriptRoot -Parent
$bitmap = [System.Drawing.Bitmap]::new(576, 576)
$g = [System.Drawing.Graphics]::FromImage($bitmap)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.ScaleTransform(4, 4)
function Brush($hex) { [System.Drawing.SolidBrush]::new([System.Drawing.ColorTranslator]::FromHtml($hex)) }
$bg = Brush '#24647A'
$white = Brush '#F5F8FA'
$heart = Brush '#E2917D'
$round = [System.Drawing.Drawing2D.GraphicsPath]::new()
$round.AddArc(0,0,64,64,180,90); $round.AddArc(80,0,64,64,270,90)
$round.AddArc(80,80,64,64,0,90); $round.AddArc(0,80,64,64,90,90); $round.CloseFigure()
$g.FillPath($bg, $round)
$map = [System.Drawing.Drawing2D.GraphicsPath]::new()
$points = [System.Drawing.PointF[]]@([System.Drawing.PointF]::new(21,97),[System.Drawing.PointF]::new(49,88),[System.Drawing.PointF]::new(91,101),[System.Drawing.PointF]::new(123,90),[System.Drawing.PointF]::new(123,117),[System.Drawing.PointF]::new(91,127),[System.Drawing.PointF]::new(49,114),[System.Drawing.PointF]::new(21,123))
$map.AddPolygon($points)
$pen = [System.Drawing.Pen]::new([System.Drawing.ColorTranslator]::FromHtml('#C8E4DF'),3)
$pen.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
$g.DrawPath($pen,$map); $pen.Width = 2
$g.DrawLine($pen,49,89,49,113); $g.DrawLine($pen,91,102,91,126)
$pin = [System.Drawing.Drawing2D.GraphicsPath]::new()
$pin.AddBezier(72,19,51,19,35,34,35,54)
$pin.AddBezier(35,54,35,81,72,107,72,107)
$pin.AddBezier(72,107,72,107,109,81,109,54)
$pin.AddBezier(109,54,109,34,93,19,72,19); $pin.CloseFigure()
$g.FillPath($white,$pin)
$hp = [System.Drawing.Drawing2D.GraphicsPath]::new()
$hp.AddLine(72,72,55,56); $hp.AddBezier(55,56,43,44,60,31,72,44)
$hp.AddBezier(72,44,84,31,101,44,89,56); $hp.AddLine(89,56,72,72); $hp.CloseFigure()
$g.FillPath($heart,$hp)
$output = [System.Drawing.Bitmap]::new(144,144)
$scaled = [System.Drawing.Graphics]::FromImage($output)
$scaled.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$scaled.DrawImage($bitmap,0,0,144,144)
$output.Save((Join-Path $root 'assets/brand/icon-144.png'),[System.Drawing.Imaging.ImageFormat]::Png)
$scaled.Dispose(); $output.Dispose(); $g.Dispose(); $bitmap.Dispose()
@($bg,$white,$heart,$round,$map,$pen,$pin,$hp) | ForEach-Object { $_.Dispose() }
