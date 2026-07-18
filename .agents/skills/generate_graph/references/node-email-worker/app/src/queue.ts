export type EmailJob = {
  userEmail: string;
};

export function subscribeToEmailJobs(
  handler: (job: EmailJob) => Promise<void>
) {
  return handler;
}
