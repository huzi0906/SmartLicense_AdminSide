using System.Collections.Generic;

namespace SmartLicense_AdminSide.Models
{
    public class FeedbackDetailViewModel
    {
        public string UserId { get; set; }
        public string UserName { get; set; }
        public string UserCNIC { get; set; }
        public List<ConversationMessage> Messages { get; set; }
    }
}
