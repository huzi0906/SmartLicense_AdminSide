// Conversation message
using System;
using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;

namespace SmartLicense_AdminSide.Models
{
    public class ConversationMessage
    {
        [BsonId]
        [BsonRepresentation(BsonType.ObjectId)]
        public required string Id { get; set; }

        [BsonRepresentation(BsonType.ObjectId)]
        public required string ConversationId { get; set; }
        
        public required string Message { get; set; }
        
        public DateTime SentAt { get; set; }
        
        public bool IsAdminMessage { get; set; }
    }
}