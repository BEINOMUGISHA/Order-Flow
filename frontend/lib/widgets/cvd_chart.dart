import 'dart:math';
import 'package:flutter/material.dart';
import '../models/order_flow_models.dart';

class CvdChartWidget extends StatelessWidget {
  final List<FootprintBar> completedBars;
  final FootprintBar? activeBar;

  const CvdChartWidget({
    super.key,
    required this.completedBars,
    this.activeBar,
  });

  @override
  Widget build(BuildContext context) {
    List<FootprintBar> allBars = List.from(completedBars);
    if (activeBar != null) {
      allBars.add(activeBar!);
    }

    if (allBars.isEmpty) {
      return Container(
        color: const Color(0xFF0F172A),
        child: const Center(
          child: Text('No CVD Data Available', style: TextStyle(color: Colors.white30)),
        ),
      );
    }

    return Container(
      color: const Color(0xFF0B132B),
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Row(
            children: [
              Icon(Icons.show_chart, color: Colors.cyanAccent, size: 18),
              SizedBox(width: 8),
              Text(
                'CUMULATIVE VOLUME DELTA (CVD) SESSION LINE',
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                  letterSpacing: 1.1,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Expanded(
            child: CustomPaint(
              size: Size.infinite,
              painter: CvdLineCustomPainter(allBars: allBars),
            ),
          ),
        ],
      ),
    );
  }
}

class CvdLineCustomPainter extends CustomPainter {
  final List<FootprintBar> allBars;

  CvdLineCustomPainter({required this.allBars});

  @override
  void paint(Canvas canvas, Size size) {
    if (allBars.isEmpty) return;

    double minCvd = double.infinity;
    double maxCvd = -double.infinity;

    for (var b in allBars) {
      minCvd = min(minCvd, b.cvd);
      maxCvd = max(maxCvd, b.cvd);
    }

    if (minCvd == maxCvd) {
      minCvd -= 1.0;
      maxCvd += 1.0;
    }

    double cvdRange = maxCvd - minCvd;
    double stepX = size.width / max(1, allBars.length - 1);

    final Paint linePaint = Paint()
      ..color = Colors.cyanAccent
      ..strokeWidth = 2.5
      ..style = PaintingStyle.stroke;

    final Paint zeroLinePaint = Paint()
      ..color = Colors.white24
      ..strokeWidth = 1.0;

    // Draw Zero Line
    double zeroY = size.height * (1.0 - (0.0 - minCvd) / cvdRange);
    if (zeroY >= 0 && zeroY <= size.height) {
      canvas.drawLine(Offset(0, zeroY), Offset(size.width, zeroY), zeroLinePaint);
    }

    Path cvdPath = Path();
    List<Offset> points = [];

    for (int i = 0; i < allBars.length; i++) {
      double x = i * stepX;
      double y = size.height * (1.0 - (allBars[i].cvd - minCvd) / cvdRange);
      Offset pt = Offset(x, y);
      points.add(pt);

      if (i == 0) {
        cvdPath.moveTo(pt.dx, pt.dy);
      } else {
        cvdPath.lineTo(pt.dx, pt.dy);
      }
    }

    canvas.drawPath(cvdPath, linePaint);

    // Draw Dots & Divergence Markers
    for (int i = 0; i < allBars.length; i++) {
      FootprintBar bar = allBars[i];
      Offset pt = points[i];

      Color dotColor = bar.delta >= 0 ? Colors.greenAccent : Colors.redAccent;
      canvas.drawCircle(pt, 4.0, Paint()..color = dotColor);

      // Check CVD / Price Divergence
      // Price makes higher high while CVD makes lower high (Bearish Divergence)
      // Price makes lower low while CVD makes higher low (Bullish Divergence)
      if (i > 0) {
        FootprintBar prev = allBars[i - 1];
        bool priceUp = bar.close > prev.close;
        bool cvdUp = bar.cvd > prev.cvd;

        if (priceUp && !cvdUp) {
          // Bearish Divergence
          _drawDivergenceMarker(canvas, pt, 'BEAR DIVERGENCE', Colors.redAccent);
        } else if (!priceUp && cvdUp) {
          // Bullish Divergence
          _drawDivergenceMarker(canvas, pt, 'BULL DIVERGENCE', Colors.greenAccent);
        }
      }
    }
  }

  void _drawDivergenceMarker(Canvas canvas, Offset pt, String label, Color color) {
      canvas.drawCircle(pt, 7.0, Paint()..color = color.withValues(alpha: 0.3));
    TextPainter tp = TextPainter(
      text: TextSpan(
        text: '▲ $label',
        style: TextStyle(color: color, fontSize: 9, fontWeight: FontWeight.bold),
      ),
      textDirection: TextDirection.ltr,
    );
    tp.layout();
    tp.paint(canvas, Offset(pt.dx - (tp.width / 2), pt.dy - 16));
  }

  @override
  bool shouldRepaint(covariant CvdLineCustomPainter oldDelegate) => true;
}
