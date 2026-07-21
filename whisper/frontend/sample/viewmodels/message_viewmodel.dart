import 'dart:async';

import 'package:flutter/material.dart';
import 'package:toko/sample/models/message.dart';
import 'package:toko/sample/services/websocket_service.dart';

class MessageViewmodel extends ChangeNotifier {
  final _websocketService = WebsocketService();
  List<Message> messageList = [];
  StreamSubscription? _subscription;
  int clientsConnected = 0;

  Future<void> sendMessage(String message)async{
    _websocketService.sendMessage(message);
  }

  void initWebsocket(){
    _websocketService.connect();
    _subscription?.cancel();
    _subscription = _websocketService.eventStream.listen((event) => _handleEvent(event));
  }
  
  void _handleEvent(Map<String, dynamic> event){
    final type = event['type'];
    final data = event['data'];

    if(type == "total-clients"){
      _handleClientConnection(Map<String, dynamic>.from(data));
    }else if(type == "message"){
      _handleMessage(Map<String, dynamic>.from(data));
    }
  }

  void _handleClientConnection(Map<String, dynamic> data){
    clientsConnected = data['clients'];
    notifyListeners();
  }

  void _handleMessage(Map<String, dynamic> data){
    final message = Message(message: data['message'], createAt: DateTime.now());
    messageList.add(message);
    notifyListeners();
  }
}