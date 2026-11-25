This project is a parent that hold all of my projects. I have created a workflow where I give you TODOS and you ask me for direction using QUESTIONS so that I can stay in the loop. Each of my projects has its own AGENTTODOS and QUESTIONS files. 


Coding guidelines

Mobile will be the main use of this website. Always make everything with mobile look as priority\n 
Make all sx={} be on one line. There can be exceptions. but normally do this\n 
make all imports in one line instead of stacking them vertically\n 
net negative code changes are always preferred over net positive\n 
For table models in the backend, make all fields only be one line\n 
Never use enums\n 
Always use bootstrap and minimize custom CSS (unless necessary)\n 
for handling mobile, use bootstrap such as col-12, p-0, then for bigger screens on that tag use like col-md-4, p-md-2 (these are examples not an exact template)\n 
for all DB reads use raw sql with parameters in lowercase\n 
use native div, detail, summary, i, container tags\n 
all html tags with words within the tag make 1 line (i like vertically compact code)\n 
Image standard: when a user uploads an image(s), convert to AVIF and upload the image after that to s3 or filesystem. If the conversion to AVIF fails, keep the original format\n 
table changes: for fastapi add a small script in the lifespan joint\n 
always NPM run build for UI after making changes\n 
make all date, pickers first have you pick the year, then have you pick the month, then have you pick the day\n 
New apps should follow the same stack and coding style as the existing DAVID and KC apps.\n 
Make all READMEs and all .md files just text - no special md stuff except accordions\n 
