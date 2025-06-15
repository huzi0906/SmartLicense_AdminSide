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
        public string Id { get; set; } = null!;

        [BsonRepresentation(BsonType.ObjectId)]
        public string UserId { get; set; } = null!;
        
        public DateTime CreatedAt { get; set; }
        
        public DateTime LastUpdatedAt { get; set; }
        
        public List<ConversationMessage> Messages { get; set; } = new List<ConversationMessage>();
    }
}
