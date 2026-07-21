import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:toko/sample/viewmodels/message_viewmodel.dart';

class MessageView extends StatefulWidget {
  const MessageView({super.key});

  @override
  State<MessageView> createState() => _MessageViewState();
}

class _MessageViewState extends State<MessageView> {
  final messageController = TextEditingController();
  
  @override
  void initState() {
    super.initState();
    Future.microtask((){
      final messageVM = Provider.of<MessageViewmodel>(context, listen: false);
      messageVM.initWebsocket();
    });
  }

  @override
  Widget build(BuildContext context) {
    final messageVM = Provider.of<MessageViewmodel>(context);

    return Scaffold(
      appBar: AppBar(title: Text("Messages ${messageVM.clientsConnected}"), backgroundColor: Colors.orange,),
      body: Consumer<MessageViewmodel>(
        builder: (context, vm, child) {
          return Column(
            mainAxisSize: MainAxisSize.max,
            children: [
              ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: vm.messageList.length,
                itemBuilder: (context, index) {
                  final message = vm.messageList[index];
                  return ListTile(
                    title: Text(message.message),
                    subtitle: Text(DateFormat("HH:mm").format(message.createAt)),
                  );
                },
              ),
              Row(
                children: [
                  Container(
                    width: 500,
                    height: 200,
                      child: TextField(
                      controller: messageController, 
                      decoration: InputDecoration(labelText: "Typing message..."),
                      onSubmitted: (value) {
                        if(messageController.text.isNotEmpty){
                          vm.sendMessage(messageController.text);
                          setState(() {
                            messageController.clear();
                          });
                        }
                      },),
                    ),
                  InkWell(
                    onTap: (){
                      if(messageController.text.isNotEmpty){
                        vm.sendMessage(messageController.text);
                        setState(() {
                          messageController.clear();
                        });
                      }
                    },
                    child: Icon(Icons.send),
                  )
                ],
              )
            ],
          );
        },
      )
    );
  }
}