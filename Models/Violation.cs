using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;
using System.Collections.Generic;

namespace SmartLicense_AdminSide.Models
{
    public class Violation
    {
        [BsonId]
        [BsonRepresentation(BsonType.ObjectId)]
        public string? Id { get; set; }
        
        [BsonElement("userCnic")]
        public string UserCnic { get; set; } = string.Empty; // Reference to the user
        
        [BsonElement("type")]
        public string Type { get; set; } = string.Empty; // "reverse_parking", "parallel_parking", "hands_off_steering", "seatbelt_violation", "driver_eye_violation"
        
        [BsonElement("timestamp")]
        public string Timestamp { get; set; } = string.Empty; // ISO timestamp string
        
        [BsonElement("imageBase64")]
        public string ImageBase64 { get; set; } = string.Empty; // Base64 encoded image data
        
        [BsonElement("severity")]
        public string Severity { get; set; } = string.Empty; // "low", "medium", "high"
        
        [BsonElement("description")]
        public string Description { get; set; } = string.Empty; // Human-readable description of the violation
        
        [BsonElement("testDate")]
        public DateTime TestDate { get; set; } = DateTime.UtcNow; // When the test was conducted
    }
}
