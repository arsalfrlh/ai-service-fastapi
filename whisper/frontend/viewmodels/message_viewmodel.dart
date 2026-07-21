import 'dart:async';

import 'package:flutter/material.dart';
import 'package:toko/models/message.dart';
import 'package:toko/services/api_service.dart';
import 'package:toko/services/websocket_service.dart';

class MessageViewmodel extends ChangeNotifier {
  final _apiService = ApiService();
  final _websocketService = WebsocketService();
  List<Message> messageList = [];
  bool isLoading = false;
  bool isAction = false;
  StreamSubscription? _subscription;
  bool isTyping = false;

  void initWebsocket(){
    _websocketService.connect();
  }

  Future<void> sendMessage(String message, List<String> imagePaths)async{
    isAction = true;
    notifyListeners();
    await _apiService.sendMessage(message, imagePaths);
    isAction = false;
    notifyListeners();
  }

  Future<void> fetchMessage()async{
    isLoading = true;
    notifyListeners();
    messageList = await _apiService.getAllMessage();
    _subscription?.cancel();
    _subscription = _websocketService.websocketEvent.listen((event) => _handleEvent(event));
    isLoading = false;
    notifyListeners();
  }

  void _handleEvent(Map<String, dynamic> event){
    final type = event['type'];
    final data = Map<String, dynamic>.from(event['data']);

    if(type == "ai-response"){
      _handleResponseAi(data);
    }else if(type == "message"){
      _handleMessage(data);
    }
  }

  void _handleResponseAi(Map<String, dynamic> data){
    final chunk = data['chunk'];
    final done = data['done'];

    if(!messageList.any((m) => m.isStreaming == true)){
      messageList.add(Message(role: "assistant", content: "", isStreaming: true, createAt: DateTime.now()));
    }

    final index = messageList.indexWhere((m) => m.isStreaming == true);
    if(index != -1){
      isTyping = true;
      messageList[index].content += chunk;
    }
    notifyListeners();
  }

  void _handleMessage(Map<String, dynamic> data){
    final action = data['action'];
    final message = Message.fromJson(data['message']);

    if(action == "create"){
      if(message.role == "assistant"){
        isTyping = false;
        final index = messageList.indexWhere((m) => m.isStreaming == true);
        if(index != -1){
          messageList[index] = message;
        }else{
          messageList.add(message);
        }
      }else{
        messageList.add(message);
      }
    }
    notifyListeners();
  }
}