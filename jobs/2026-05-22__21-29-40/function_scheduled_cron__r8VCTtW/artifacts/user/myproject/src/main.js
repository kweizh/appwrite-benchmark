export default async ({ req, res, log, error }) => {
  return res.json({
    ok: true,
    ts: new Date().toISOString(),
  });
};
