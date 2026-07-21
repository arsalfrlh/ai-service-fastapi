import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

class WebsocketService {
  static final _instance = WebsocketService._internal();
  factory WebsocketService(){
    return _instance;
  }
  WebsocketService._internal();

  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  final _controller = StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get eventStream => _controller.stream;
  bool _isConnected = false;

  void connect(){
    if(_isConnected) return;
    final wsUrl = "ws://127.0.0.1:8000/ws";
    _channel = WebSocketChannel.connect(Uri.parse(wsUrl));
    _subscription = _channel?.stream.listen((event){
      final data = jsonDecode(event);
      print("Data Event: $data");

      if(data['event'] == "websocket:connected"){
        _isConnected = true;
      }

      if(data['event'] == "client:connected"){
        final payload = data['data'];
        _controller.add({
          "type": "total-clients",
          "data": payload
        });
      }

      if(data['event'] == "client:broadcast"){
        final payload = data['data'];
        _controller.add({
          "type": "message",
          "data": payload
        });
      }
    });
  }

  void sendMessage(String message){
    _channel?.sink.add(jsonEncode({
      "event": "call:broadcast",
      "data": {
        "message": message
      }
    }));
  }

  void disconnect(){
    _subscription?.cancel();
    _subscription = null;
    _channel?.sink.close();
    _channel = null;
    _isConnected = false;
  }
}