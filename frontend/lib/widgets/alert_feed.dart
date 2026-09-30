import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/order_flow_models.dart';

class AlertFeedWidget extends StatelessWidget {
  final List<AlertPayload> alerts;

  const AlertFeedWidget({super.key, required this.alerts});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF0F172A),
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Row(
                children: [
                  const Icon(Icons.notifications_active,
                      color: Colors.amberAccent, size: 18),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      'AUDITABLE LIVE SIGNAL & ALERT FEED',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                        letterSpacing: 1.1,
                      ),
                    ),
                  ),
                ],
              ),
              Align(
                alignment: Alignment.centerRight,
                child: Text(
                  'Total Alerts: ${alerts.length}',
                  style: const TextStyle(color: Colors.white54, fontSize: 11),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Expanded(
            child: alerts.isEmpty
                ? const Center(
                    child: Text('No Signal Alerts Triggered Yet',
                        style: TextStyle(color: Colors.white30)),
                  )
                : ListView.separated(
                    itemCount: alerts.length,
                    separatorBuilder: (_, __) =>
                        const Divider(color: Color(0xFF1E293B), height: 1),
                    itemBuilder: (context, index) {
                      AlertPayload alert =
                          alerts[alerts.length - 1 - index]; // reverse order
                      return _buildAlertTile(alert);
                    },
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildAlertTile(AlertPayload alert) {
    Color tierColor;
    switch (alert.confidenceTier) {
      case 'HIGH':
        tierColor = Colors.greenAccent;
        break;
      case 'MEDIUM':
        tierColor = Colors.amberAccent;
        break;
      case 'LOW':
        tierColor = Colors.orangeAccent;
        break;
      default:
        tierColor = Colors.redAccent;
    }

    String timeStr = DateFormat('HH:mm:ss').format(
      DateTime.fromMillisecondsSinceEpoch(alert.timestamp),
    );

    return ExpansionTile(
      tilePadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 0),
      leading: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
        decoration: BoxDecoration(
          color: tierColor.withValues(alpha: 0.15),
          border: Border.all(color: tierColor, width: 1),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(
          '${(alert.confidenceScore * 100).toInt()}%',
          style: TextStyle(
              color: tierColor, fontWeight: FontWeight.bold, fontSize: 11),
        ),
      ),
      title: Row(
        children: [
          Text(
            alert.alertType,
            style: const TextStyle(
                color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
          ),
          const SizedBox(width: 8),
          Text(
            '@ \$${alert.price.toStringAsFixed(1)}',
            style: const TextStyle(color: Colors.cyanAccent, fontSize: 12),
          ),
        ],
      ),
      subtitle: Text(
        '$timeStr • Tier: ${alert.confidenceTier}',
        style: const TextStyle(color: Colors.white54, fontSize: 10),
      ),
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          color: const Color(0xFF1E293B),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'RAW AUDIT METRICS:',
                style: TextStyle(
                    color: Colors.white70,
                    fontWeight: FontWeight.bold,
                    fontSize: 10),
              ),
              const SizedBox(height: 4),
              Text(
                alert.rawMetrics.toString(),
                style: const TextStyle(
                    color: Colors.white54,
                    fontSize: 10,
                    fontFamily: 'monospace'),
              ),
              const SizedBox(height: 6),
              const Text(
                'THRESHOLDS USED:',
                style: TextStyle(
                    color: Colors.white70,
                    fontWeight: FontWeight.bold,
                    fontSize: 10),
              ),
              Text(
                alert.thresholdUsed.toString(),
                style: const TextStyle(
                    color: Colors.white54,
                    fontSize: 10,
                    fontFamily: 'monospace'),
              ),
              if (alert.failureModes.isNotEmpty) ...[
                const SizedBox(height: 6),
                const Text(
                  'DISCLOSED FAILURE MODES:',
                  style: TextStyle(
                      color: Colors.amber,
                      fontWeight: FontWeight.bold,
                      fontSize: 10),
                ),
                ...alert.failureModes.map((fm) => Text('• $fm',
                    style: const TextStyle(
                        color: Colors.amberAccent, fontSize: 10))),
              ],
            ],
          ),
        ),
      ],
    );
  }
}
