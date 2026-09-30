import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

class WebSocketService {
  final String url;
  WebSocketChannel? _channel;
  final StreamController<Map<String, dynamic>> _streamController =
      StreamController<Map<String, dynamic>>.broadcast();

  bool isConnected = false;
  Timer? _reconnectTimer;
  String? _symbol;
  int _connectionGeneration = 0;

  Stream<Map<String, dynamic>> get stream => _streamController.stream;

  WebSocketService({
    this.url = const String.fromEnvironment(
      'ORDERFLOW_WS_URL',
      defaultValue: 'ws://localhost:8000/ws/orderflow',
    ),
  });

  void connect({String? symbol}) {
    if (symbol != null) _symbol = symbol;
    final generation = ++_connectionGeneration;
    final baseUri = Uri.parse(url);
    final queryParameters = Map<String, String>.from(baseUri.queryParameters);
    if (_symbol != null) queryParameters['symbol'] = _symbol!;
    final connectionUri = baseUri.replace(queryParameters: queryParameters);

    try {
      _channel?.sink.close();
      _channel = WebSocketChannel.connect(connectionUri);
      isConnected = true;

      _channel!.stream.listen(
        (data) {
          if (generation != _connectionGeneration) return;
          try {
            final Map<String, dynamic> jsonMsg = jsonDecode(data);
            _streamController.add(jsonMsg);
          } catch (e) {
            debugPrint('Error parsing WS message: $e');
          }
        },
        onError: (error) {
          if (generation != _connectionGeneration) return;
          debugPrint('WS Stream error: $error');
          _handleDisconnect(generation);
        },
        onDone: () {
          if (generation != _connectionGeneration) return;
          debugPrint('WS Connection closed');
          _handleDisconnect(generation);
        },
      );
    } catch (e) {
      if (generation != _connectionGeneration) return;
      debugPrint('WS Connect exception: $e');
      _handleDisconnect(generation);
    }
  }

  void _handleDisconnect(int generation) {
    if (generation != _connectionGeneration) return;
    isConnected = false;
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 2), () {
      debugPrint('Attempting WS reconnect...');
      connect();
    });
  }

  void dispose() {
    _connectionGeneration++;
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _streamController.close();
  }
}
