export default async ({ req, res, log, error }) => {
  if (req.method === 'GET' && req.path === '/greeting') {
    const name = req.query.name || 'world';
    return res.json({ message: `Hello, ${name}` });
  }

  return res.json({ error: 'not found' }, 404);
};
