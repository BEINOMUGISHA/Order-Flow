import 'package:flutter/material.dart';
import '../models/order_flow_models.dart';

class HealthBannerWidget extends StatelessWidget {
  final HealthStatus health;

  const HealthBannerWidget({super.key, required this.health});

  @override
  Widget build(BuildContext context) {
    Color statusColor;
    IconData icon;

    switch (health.state) {
      case 'OK':
        statusColor = Colors.greenAccent;
        icon = Icons.check_circle;
        break;
      case 'DATA_GAP_DETECTED':
        statusColor = Colors.redAccent;
        icon = Icons.warning;
        break;
      case 'RESYNCING':
        statusColor = Colors.amberAccent;
        icon = Icons.sync;
        break;
      default:
        statusColor = Colors.grey;
        icon = Icons.cloud_off;
    }

    return Container(
      color: const Color(0xFF1E293B),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              Icon(icon, color: statusColor, size: 20),
              const SizedBox(width: 8),
              Text(
                'STREAM HEALTH: ${health.state}',
                style: TextStyle(
                  color: statusColor,
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                  letterSpacing: 1.1,
                ),
              ),
              const SizedBox(width: 12),
              Text(
                '• ${health.message}',
                style: const TextStyle(color: Colors.white70, fontSize: 12),
              ),
            ],
          ),
          Row(
            children: [
              _buildMetricChip('Gaps', '${health.gapCount}', health.gapCount > 0 ? Colors.redAccent : Colors.white70),
              const SizedBox(width: 12),
              _buildMetricChip('Seq ID', '${health.lastSequenceId ?? "N/A"}', Colors.cyanAccent),
              const SizedBox(width: 12),
              _buildMetricChip('Latency', '${health.avgLatencyMs.toStringAsFixed(1)} ms', Colors.white70),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMetricChip(String label, String value, Color valueColor) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Row(
        children: [
          Text('$label: ', style: const TextStyle(color: Colors.white54, fontSize: 11)),
          Text(value, style: TextStyle(color: valueColor, fontWeight: FontWeight.bold, fontSize: 11)),
        ],
      ),
    );
  }
}
