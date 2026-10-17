# Overview
This project is a parent that hold all of my projects. I have created a workflow where I give you TODOS and you ask me for direction using QUESTIONS so that I can stay in the loop. Each of my projects has its own AGENTTODOS and QUESTIONS files. 

## Coding Style
- Mobile will be the main use of this website. Always make everything with mobile look as priority
- Make all sx={} be on one line. There can be exceptions. but normally do this
- make all imports in one line instead of stacking them vertically
- net negative code changes are always preferred over net positive
- For table models in the backend, make all fields only be one line
- Never use enums
- Always use bootstrap and minimize custom CSS (unless necessary)
- for handling mobile, use bootstrap such as col-12, p-0, then for bigger screens on that tag use like col-md-4, p-md-2 (these are examples not an exact template)
- for all DB reads use raw sql with parameters in lowercase
- use native div, detail, summary, i, container tags
- all html tags with words within the tag make 1 line (i like vertically compact code)
- Image standard: when a user uploads an image(s), convert to AVIF and upload the image after that to s3 or filesystem. If the conversion to AVIF fails, keep the original format
- table changes: for fastapi add a small script in the lifespan joint
