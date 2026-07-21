import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

class WebsocketService {
  static final _instance = WebsocketService._internal();
  factory WebsocketService(){
    return _instance;
  }
  WebsocketService._internal();

  final _streamController = StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get websocketEvent => _streamController.stream;
  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  bool _isConnected = false;

  void connect(){
    if(_isConnected) return;
    final wsUrl = "ws://127.0.0.1:8000/ws";
    _channel = WebSocketChannel.connect(Uri.parse(wsUrl));
    _subscription = _channel?.stream.listen((event){
      final data = jsonDecode(event);
      print("Data Event: $data");

      if(data['event'] == "connected"){
        _isConnected = true;
      }

      if(data['event'] == "message"){
        final payload = data['data'];
        _streamController.add({
          "type": "message",
          "data": payload
        });
      }

      if(data['event'] == "ai-response"){
        final payload = data['data'];
        _streamController.add({
          "type": "ai-response",
          "data": payload
        });
      }
    },
    onDone: () {
      _isConnected = false;
      _reconnect();
    },
    onError: (e){
      _isConnected = false;
      _reconnect();
    });
  }

  void _reconnect(){
    Future.delayed(Duration(seconds: 5),(){
      connect();
    });
  }

  void disconnect(){
    _subscription?.cancel();
    _subscription = null;
    _channel?.sink.close();
    _channel = null;
    _isConnected = false;
  }
}