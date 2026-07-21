class Message {
  final String role;
  String content;
  bool isStreaming;
  final DateTime createAt;

  Message({required this.role, required this.content, required this.isStreaming, required this.createAt});
  factory Message.fromJson(Map<String, dynamic> json){
    return Message(
      role: json['role'],
      content: json['content'],
      isStreaming: false,
      createAt: DateTime.now()
    );
  }
}