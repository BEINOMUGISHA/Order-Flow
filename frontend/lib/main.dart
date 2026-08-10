
import 'package:flutter/material.dart';
import 'models/order_flow_models.dart';
import 'services/websocket_service.dart';
import 'widgets/footprint_chart.dart';
import 'widgets/cvd_chart.dart';
import 'widgets/alert_feed.dart';
import 'widgets/health_banner.dart';

void main() {
  runApp(const OrderFlowApp());
}

class OrderFlowApp extends StatelessWidget {
  const OrderFlowApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Real-Time Order Flow Engine',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0B132B),
        primaryColor: Colors.cyanAccent,
        appBarTheme: const AppBarTheme(backgroundColor: Color(0xFF0F172A), elevation: 0),
        expansionTileTheme: const ExpansionTileThemeData(
          iconColor: Colors.white54,
          collapsedIconColor: Colors.white38,
          textColor: Colors.white,
          collapsedTextColor: Colors.white70,
        ),
      ),
      home: const OrderFlowDashboardScreen(),
    );
  }
}

class OrderFlowDashboardScreen extends StatefulWidget {
  const OrderFlowDashboardScreen({super.key});

  @override
  State<OrderFlowDashboardScreen> createState() => _OrderFlowDashboardScreenState();
}

class _OrderFlowDashboardScreenState extends State<OrderFlowDashboardScreen> {
  final WebSocketService _wsService = WebSocketService();

  HealthStatus _health = HealthStatus(
    state: 'DISCONNECTED',
    gapCount: 0,
    avgLatencyMs: 0.0,
    message: 'Connecting to WebSocket Server...',
  );

  List<FootprintBar> _completedBars = [];
  FootprintBar? _activeBar;
  double _sessionCvd = 0.0;
  List<AlertPayload> _alerts = [];

  @override
  void initState() {
    super.initState();
    _wsService.connect();
    _wsService.stream.listen((message) {
      _handleServerMessage(message);
    });
  }

  void _handleServerMessage(Map<String, dynamic> msg) {
    setState(() {
      final String type = msg['type'] ?? '';

      if (type == 'INITIAL_STATE') {
        if (msg['health'] != null) {
          _health = HealthStatus.fromJson(msg['health']);
        }
        if (msg['completed_bars'] != null) {
          _completedBars = (msg['completed_bars'] as List)
              .map((b) => FootprintBar.fromJson(b))
              .toList();
        }
        if (msg['active_bar'] != null) {
          _activeBar = FootprintBar.fromJson(msg['active_bar']);
        }
        _sessionCvd = (msg['session_cvd'] as num? ?? 0).toDouble();
        if (msg['alerts'] != null) {
          _alerts = (msg['alerts'] as List)
              .map((a) => AlertPayload.fromJson(a))
              .toList();
        }
      } else if (type == 'TICK_UPDATE') {
        if (msg['health'] != null) _health = HealthStatus.fromJson(msg['health']);
        if (msg['active_bar'] != null) _activeBar = FootprintBar.fromJson(msg['active_bar']);
        if (msg['completed_bar'] != null) {
          _completedBars.add(FootprintBar.fromJson(msg['completed_bar']));
          // Keep only last 30 bars to avoid unbounded memory growth
          if (_completedBars.length > 30) {
            _completedBars.removeAt(0);
          }
        }
        _sessionCvd = (msg['session_cvd'] as num? ?? _sessionCvd).toDouble();
        if (msg['alerts'] != null) {
          final newAlerts = (msg['alerts'] as List)
              .map((a) => AlertPayload.fromJson(a))
              .toList();
          _alerts.addAll(newAlerts);
          // Keep only last 200 alerts
          if (_alerts.length > 200) {
            _alerts = _alerts.sublist(_alerts.length - 200);
          }
        }
      }
    });
  }

  @override
  void dispose() {
    _wsService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.cyanAccent.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: Colors.cyanAccent),
              ),
              child: const Text(
                'BTCUSDT.PERP',
                style: TextStyle(color: Colors.cyanAccent, fontWeight: FontWeight.bold, fontSize: 13),
              ),
            ),
            const SizedBox(width: 12),
            const Text(
              'REAL-TIME ORDER FLOW ENGINE',
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 1.1),
            ),
          ],
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Center(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: const Color(0xFF334155)),
                ),
                child: Row(
                  children: [
                    const Text('SESSION CVD: ', style: TextStyle(color: Colors.white54, fontSize: 12)),
                    Text(
                      '${_sessionCvd >= 0 ? "+" : ""}${_sessionCvd.toStringAsFixed(2)}',
                      style: TextStyle(
                        color: _sessionCvd >= 0 ? Colors.greenAccent : Colors.redAccent,
                        fontWeight: FontWeight.bold,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          HealthBannerWidget(health: _health),
          Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Left: Footprint chart (70%) + CVD (30%)
                Expanded(
                  flex: 7,
                  child: Column(
                    children: [
                      Expanded(
                        flex: 7,
                        child: FootprintChartWidget(
                          completedBars: _completedBars,
                          activeBar: _activeBar,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Expanded(
                        flex: 3,
                        child: CvdChartWidget(
                          completedBars: _completedBars,
                          activeBar: _activeBar,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(color: const Color(0xFF1E293B), width: 1),
                // Right: Alert feed
                Expanded(
                  flex: 3,
                  child: AlertFeedWidget(alerts: _alerts),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
