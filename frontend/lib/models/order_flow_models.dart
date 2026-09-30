class MarketInfo {
  final String symbol;
  final String provider;
  final String assetClass;
  final double tickSize;

  MarketInfo({
    required this.symbol,
    required this.provider,
    required this.assetClass,
    required this.tickSize,
  });

  factory MarketInfo.fromJson(Map<String, dynamic> json) {
    return MarketInfo(
      symbol: json['symbol'] ?? '',
      provider: json['provider'] ?? '',
      assetClass: json['asset_class'] ?? 'other',
      tickSize: (json['tick_size'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class FootprintLevel {
  final double price;
  final double bidVol;
  final double askVol;
  final double totalVol;
  final double delta;
  final String imbalanceFlag; // 'BUY_IMBALANCE', 'SELL_IMBALANCE', 'NONE'

  FootprintLevel({
    required this.price,
    required this.bidVol,
    required this.askVol,
    required this.totalVol,
    required this.delta,
    required this.imbalanceFlag,
  });

  factory FootprintLevel.fromJson(Map<String, dynamic> json) {
    return FootprintLevel(
      price: (json['price'] as num).toDouble(),
      bidVol: (json['bid_vol'] as num).toDouble(),
      askVol: (json['ask_vol'] as num).toDouble(),
      totalVol: (json['total_vol'] as num).toDouble(),
      delta: (json['delta'] as num).toDouble(),
      imbalanceFlag: json['imbalance_flag'] ?? 'NONE',
    );
  }
}

class FootprintBar {
  final String barId;
  final int startTime;
  final int endTime;
  final double open;
  final double high;
  final double low;
  final double close;
  final double totalVolume;
  final double buyVolume;
  final double sellVolume;
  final double delta;
  final double cvd;
  final double pocPrice;
  final Map<String, FootprintLevel> levels;
  final bool gapFlag;
  final String confidence; // 'CONFIDENT', 'UNRELIABLE_GAP'

  FootprintBar({
    required this.barId,
    required this.startTime,
    required this.endTime,
    required this.open,
    required this.high,
    required this.low,
    required this.close,
    required this.totalVolume,
    required this.buyVolume,
    required this.sellVolume,
    required this.delta,
    required this.cvd,
    required this.pocPrice,
    required this.levels,
    required this.gapFlag,
    required this.confidence,
  });

  factory FootprintBar.fromJson(Map<String, dynamic> json) {
    Map<String, FootprintLevel> lvls = {};
    if (json['levels'] != null) {
      (json['levels'] as Map<String, dynamic>).forEach((key, val) {
        lvls[key] = FootprintLevel.fromJson(val);
      });
    }

    return FootprintBar(
      barId: json['bar_id'] ?? '',
      startTime: json['start_time'] ?? 0,
      endTime: json['end_time'] ?? 0,
      open: (json['open'] as num).toDouble(),
      high: (json['high'] as num).toDouble(),
      low: (json['low'] as num).toDouble(),
      close: (json['close'] as num).toDouble(),
      totalVolume: (json['total_volume'] as num).toDouble(),
      buyVolume: (json['buy_volume'] as num).toDouble(),
      sellVolume: (json['sell_volume'] as num).toDouble(),
      delta: (json['delta'] as num).toDouble(),
      cvd: (json['cvd'] as num).toDouble(),
      pocPrice: (json['poc_price'] as num).toDouble(),
      levels: lvls,
      gapFlag: json['gap_flag'] ?? false,
      confidence: json['confidence'] ?? 'CONFIDENT',
    );
  }
}

class AlertPayload {
  final String alertId;
  final String alertType;
  final int timestamp;
  final String symbol;
  final double price;
  final Map<String, dynamic> rawMetrics;
  final Map<String, dynamic> thresholdUsed;
  final double confidenceScore;
  final String confidenceTier;
  final List<String> failureModes;
  final bool isDebounced;

  AlertPayload({
    required this.alertId,
    required this.alertType,
    required this.timestamp,
    required this.symbol,
    required this.price,
    required this.rawMetrics,
    required this.thresholdUsed,
    required this.confidenceScore,
    required this.confidenceTier,
    required this.failureModes,
    required this.isDebounced,
  });

  factory AlertPayload.fromJson(Map<String, dynamic> json) {
    return AlertPayload(
      alertId: json['alert_id'] ?? '',
      alertType: json['alert_type'] ?? '',
      timestamp: json['timestamp'] ?? 0,
      symbol: json['symbol'] ?? '',
      price: (json['price'] as num).toDouble(),
      rawMetrics: Map<String, dynamic>.from(json['raw_metrics'] ?? {}),
      thresholdUsed: Map<String, dynamic>.from(json['threshold_used'] ?? {}),
      confidenceScore: (json['confidence_score'] as num).toDouble(),
      confidenceTier: json['confidence_tier'] ?? 'LOW',
      failureModes: List<String>.from(json['failure_modes'] ?? []),
      isDebounced: json['is_debounced'] ?? false,
    );
  }
}

class HealthStatus {
  final String state; // 'OK', 'DATA_GAP_DETECTED', 'RESYNCING', 'DISCONNECTED'
  final int gapCount;
  final int? lastSequenceId;
  final double avgLatencyMs;
  final String message;

  HealthStatus({
    required this.state,
    required this.gapCount,
    this.lastSequenceId,
    required this.avgLatencyMs,
    required this.message,
  });

  factory HealthStatus.fromJson(Map<String, dynamic> json) {
    return HealthStatus(
      state: json['state'] ?? 'OK',
      gapCount: json['gap_count'] ?? 0,
      lastSequenceId: json['last_sequence_id'],
      avgLatencyMs: (json['avg_latency_ms'] as num?)?.toDouble() ?? 0.0,
      message: json['message'] ?? 'Operating Normally',
    );
  }
}
