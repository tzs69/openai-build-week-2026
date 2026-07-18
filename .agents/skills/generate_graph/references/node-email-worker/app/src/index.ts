import { subscribeToEmailJobs } from "./queue";
import { EmailService } from "./email_service";

const emailService = new EmailService();

subscribeToEmailJobs(async (job) => {
  await emailService.sendWelcomeEmail(job.userEmail);
});
