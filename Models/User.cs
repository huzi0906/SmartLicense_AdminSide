using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;

namespace SmartLicense_AdminSide.Models
{
    [BsonIgnoreExtraElements]
    public class User
    {
        [BsonId]
        [BsonRepresentation(BsonType.ObjectId)]
        public string? Id { get; set; }
        
        [BsonElement("name")]
        public required string Name { get; set; }
        
        [BsonElement("cnic")]
        public required string CNIC { get; set; }
        
        [BsonElement("age")]
        public int Age { get; set; }
        
        [BsonElement("address")]
        public required string Address { get; set; }
        
        [BsonElement("contact")]
        public required string Contact { get; set; }
        
        [BsonElement("fatherName")]
        public required string FatherName { get; set; }
        
        [BsonElement("motherName")]
        public required string MotherName { get; set; }
        
        [BsonElement("hasLearnerLicence")]
        public bool HasLearnerLicence { get; set; }
        
        [BsonElement("hasLicence")]
        public bool HasLicence { get; set; }
    }
}