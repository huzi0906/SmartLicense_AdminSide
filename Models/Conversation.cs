//Conversation
using System;
using System.Collections.Generic;
using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;

namespace SmartLicense_AdminSide.Models
{
    public class Conversation
    {
        [BsonId]
        [BsonRepresentation(BsonType.ObjectId)]
        public required string Id { get; set; }

        [BsonRepresentation(BsonType.ObjectId)]
        public required string UserId { get; set; }
        
        public DateTime CreatedAt { get; set; }
        
        public DateTime LastUpdatedAt { get; set; }
        
        public List<ConversationMessage> Messages { get; set; } = new List<ConversationMessage>();
    }
}