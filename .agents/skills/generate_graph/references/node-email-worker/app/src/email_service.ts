import { renderWelcomeTemplate } from "./templates";
import { SmtpClient } from "./smtp_client";

export class EmailService {
  private smtpClient = new SmtpClient();

  async sendWelcomeEmail(userEmail: string) {
    const body = renderWelcomeTemplate(userEmail);
    await this.smtpClient.send(userEmail, "Welcome", body);
  }
}
