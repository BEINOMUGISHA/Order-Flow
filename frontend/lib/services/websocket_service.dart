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

  Stream<Map<String, dynamic>> get stream => _streamController.stream;

  WebSocketService({this.url = 'ws://localhost:8000/ws/orderflow'});

  void connect() {
    try {
      _channel = WebSocketChannel.connect(Uri.parse(url));
      isConnected = true;

      _channel!.stream.listen(
        (data) {
          try {
            final Map<String, dynamic> jsonMsg = jsonDecode(data);
            _streamController.add(jsonMsg);
          } catch (e) {
            debugPrint('Error parsing WS message: $e');
          }
        },
        onError: (error) {
          debugPrint('WS Stream error: $error');
          _handleDisconnect();
        },
        onDone: () {
          debugPrint('WS Connection closed');
          _handleDisconnect();
        },
      );
    } catch (e) {
      debugPrint('WS Connect exception: $e');
      _handleDisconnect();
    }
  }

  void _handleDisconnect() {
    isConnected = false;
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 2), () {
      debugPrint('Attempting WS reconnect...');
      connect();
    });
  }

  void dispose() {
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _streamController.close();
  }
}
