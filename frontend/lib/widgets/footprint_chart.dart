import 'dart:math';
import 'package:flutter/material.dart';
import '../models/order_flow_models.dart';

class FootprintChartWidget extends StatelessWidget {
  final List<FootprintBar> completedBars;
  final FootprintBar? activeBar;

  const FootprintChartWidget({
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
          child: Text(
            'Waiting for live order flow tick stream...',
            style: TextStyle(color: Colors.white70, fontSize: 16),
          ),
        ),
      );
    }

    return Container(
      color: const Color(0xFF0F172A),
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Row(
                children: [
                  Icon(Icons.candlestick_chart, color: Colors.cyanAccent),
                  SizedBox(width: 8),
                  Text(
                    'FOOTPRINT PRICE LADDER (BID x ASK)',
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                      letterSpacing: 1.1,
                    ),
                  ),
                ],
              ),
              Row(
                children: [
                  _buildLegendItem('Buy Imbalance', const Color(0xFF166534)),
                  const SizedBox(width: 12),
                  _buildLegendItem('Sell Imbalance', const Color(0xFF991B1B)),
                  const SizedBox(width: 12),
                  _buildLegendItem('POC Level', Colors.amber),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          Expanded(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: CustomPaint(
                size: Size(allBars.length * 160.0, double.infinity),
                painter: FootprintCustomPainter(allBars: allBars),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLegendItem(String label, Color color) {
    return Row(
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: const TextStyle(color: Colors.white70, fontSize: 11),
        ),
      ],
    );
  }
}

class FootprintCustomPainter extends CustomPainter {
  final List<FootprintBar> allBars;

  FootprintCustomPainter({required this.allBars});

  @override
  void paint(Canvas canvas, Size size) {
    if (allBars.isEmpty) return;

    // Find global High and Low price across all visible bars
    double minPrice = double.infinity;
    double maxPrice = -double.infinity;

    for (var b in allBars) {
      minPrice = min(minPrice, b.low);
      maxPrice = max(maxPrice, b.high);
    }

    if (minPrice == maxPrice) {
      minPrice -= 1.0;
      maxPrice += 1.0;
    }

    double priceRange = maxPrice - minPrice;
    double candleWidth = 140.0;
    double gap = 20.0;
    double topMargin = 40.0;
    double bottomMargin = 80.0;
    double chartHeight = size.height - topMargin - bottomMargin;

    final Paint gridPaint = Paint()
      ..color = const Color(0xFF1E293B)
      ..strokeWidth = 1.0;

    final Paint borderPaint = Paint()
      ..color = const Color(0xFF334155)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;

    // Draw Price Grid Lines
    int priceSteps = 10;
    for (int i = 0; i <= priceSteps; i++) {
      double y = topMargin + (chartHeight * i / priceSteps);
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);

      double priceVal = maxPrice - (priceRange * i / priceSteps);
      TextPainter tp = TextPainter(
        text: TextSpan(
          text: priceVal.toStringAsFixed(1),
          style: const TextStyle(color: Colors.white30, fontSize: 9),
        ),
        textDirection: TextDirection.ltr,
      );
      tp.layout();
      tp.paint(canvas, Offset(2, y - 10));
    }

    // Paint each Footprint Candle Bar
    for (int i = 0; i < allBars.length; i++) {
      FootprintBar bar = allBars[i];
      double xLeft = i * (candleWidth + gap) + 30.0;
      double xCenter = xLeft + (candleWidth / 2);

      double yOpen = topMargin + chartHeight * (1.0 - (bar.open - minPrice) / priceRange);
      double yClose = topMargin + chartHeight * (1.0 - (bar.close - minPrice) / priceRange);
      double yHigh = topMargin + chartHeight * (1.0 - (bar.high - minPrice) / priceRange);
      double yLow = topMargin + chartHeight * (1.0 - (bar.low - minPrice) / priceRange);

      bool isBullish = bar.close >= bar.open;
      Color candleColor = isBullish ? const Color(0xFF22C55E) : const Color(0xFFEF4444);

      // 1. Candle Wick
      final Paint wickPaint = Paint()
        ..color = candleColor
        ..strokeWidth = 2.0;
      canvas.drawLine(Offset(xCenter, yHigh), Offset(xCenter, yLow), wickPaint);

      // 2. Candle Box outline
      double boxTop = min(yOpen, yClose);
      double boxBottom = max(yOpen, yClose);
      double boxHeight = max(boxBottom - boxTop, 4.0);

      Rect candleBox = Rect.fromLTWH(xLeft, boxTop, candleWidth, boxHeight);
      final Paint boxBgPaint = Paint()
        ..color = candleColor.withValues(alpha: 0.12)
        ..style = PaintingStyle.fill;
      canvas.drawRect(candleBox, boxBgPaint);
      canvas.drawRect(candleBox, Paint()..color = candleColor..style = PaintingStyle.stroke..strokeWidth = 1.5);

      // 3. Render Level-by-Level Bid x Ask matrix inside candle
      if (bar.levels.isNotEmpty) {
        List<FootprintLevel> sortedLevels = bar.levels.values.toList()
          ..sort((a, b) => b.price.compareTo(a.price));

        double levelHeight = max(16.0, boxHeight / max(1, sortedLevels.length));

        for (int j = 0; j < sortedLevels.length; j++) {
          FootprintLevel lvl = sortedLevels[j];
          double yLvl = topMargin + chartHeight * (1.0 - (lvl.price - minPrice) / priceRange);

          Rect lvlRect = Rect.fromLTWH(xLeft + 2, yLvl - (levelHeight / 2), candleWidth - 4, levelHeight);

          // Imbalance background fill
          if (lvl.imbalanceFlag == 'BUY_IMBALANCE') {
            canvas.drawRect(
              lvlRect,
              Paint()..color = const Color(0xFF166534).withValues(alpha: 0.75)..style = PaintingStyle.fill,
            );
          } else if (lvl.imbalanceFlag == 'SELL_IMBALANCE') {
            canvas.drawRect(
              lvlRect,
              Paint()..color = const Color(0xFF991B1B).withValues(alpha: 0.75)..style = PaintingStyle.fill,
            );
          }

          // POC level highlight (Golden border)
          if ((lvl.price - bar.pocPrice).abs() < 0.01) {
            canvas.drawRect(
              lvlRect,
              Paint()
                ..color = Colors.amber
                ..style = PaintingStyle.stroke
                ..strokeWidth = 2.0,
            );
          } else {
            canvas.drawRect(lvlRect, borderPaint);
          }

          // Bid x Ask Text Rendering
          String text = '${lvl.bidVol.toStringAsFixed(1)} x ${lvl.askVol.toStringAsFixed(1)}';
          TextPainter textPainter = TextPainter(
            text: TextSpan(
              text: text,
              style: TextStyle(
                color: lvl.imbalanceFlag != 'NONE' ? Colors.white : Colors.white70,
                fontSize: 10,
                fontWeight: lvl.imbalanceFlag != 'NONE' ? FontWeight.bold : FontWeight.normal,
              ),
            ),
            textDirection: TextDirection.ltr,
          );
          textPainter.layout();
          textPainter.paint(
            canvas,
            Offset(xCenter - (textPainter.width / 2), yLvl - (textPainter.height / 2)),
          );
        }
      }

      // 4. Bar Footer Metadata (Total Vol, Delta, CVD)
      double footerY = size.height - bottomMargin + 10.0;
      _drawText(
        canvas,
        'VOL: ${bar.totalVolume.toStringAsFixed(1)}',
        Offset(xCenter, footerY),
        Colors.white70,
        10,
      );
      _drawText(
        canvas,
        'DELTA: ${bar.delta >= 0 ? '+' : ''}${bar.delta.toStringAsFixed(1)}',
        Offset(xCenter, footerY + 14),
        bar.delta >= 0 ? Colors.greenAccent : Colors.redAccent,
        10,
        fontWeight: FontWeight.bold,
      );
      _drawText(
        canvas,
        'CVD: ${bar.cvd.toStringAsFixed(1)}',
        Offset(xCenter, footerY + 28),
        Colors.cyanAccent,
        10,
      );

      // Data Gap warning flag
      if (bar.gapFlag || bar.confidence == 'UNRELIABLE_GAP') {
        _drawText(
          canvas,
          '⚠ GAP DETECTED',
          Offset(xCenter, footerY + 44),
          Colors.amberAccent,
          9,
          fontWeight: FontWeight.bold,
        );
      }
    }
  }

  void _drawText(
    Canvas canvas,
    String text,
    Offset centerOffset,
    Color color,
    double fontSize, {
    FontWeight fontWeight = FontWeight.normal,
  }) {
    TextPainter tp = TextPainter(
      text: TextSpan(
        text: text,
        style: TextStyle(color: color, fontSize: fontSize, fontWeight: fontWeight),
      ),
      textDirection: TextDirection.ltr,
    );
    tp.layout();
    tp.paint(canvas, Offset(centerOffset.dx - (tp.width / 2), centerOffset.dy));
  }

  @override
  bool shouldRepaint(covariant FootprintCustomPainter oldDelegate) => true;
}
