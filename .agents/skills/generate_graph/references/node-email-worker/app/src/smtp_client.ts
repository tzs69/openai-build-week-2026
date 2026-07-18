export class SmtpClient {
  async send(to: string, subject: string, body: string) {
    return { to, subject, body };
  }
}
