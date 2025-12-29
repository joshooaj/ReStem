# Issues

## Open Issues

### Users cannot change the name or email

Users should be able to modify their name or email address, or delete their account completely.

### Remove email address from welcome message in header

The user doesn't need to see their email address at the top of the page

### API Support

Allow users to generate an API key and use the service through a REST api.

### Admin Page

Build an admin page where I can see all the users, how many credits they have remaining, disable their accounts, or modify the number of credits in their account, and manage their completed jobs (download, or delete the job, or delete the files and mark them as expired).

### Bulk Upload

Allow user to upload a folder of files and if they have enough credits, process them all.

### Add SSO

The user should be able to register or login using single sign-on with at least Google, GitHub, and Facebook as identity providers.

### Come up with a file management strategy

I do not want to hold on to the user's original song after it has been processed, and I don't want to keep the stem files longer than I have to. Maybe we delete the stems after 1 day to avoid holding on to copyrighted music longer than necessary?

## Completed Issues

### Back-button / route support

If you're on the dashboard and you then go to another page like "Buy Credits", if you press "back" nothing happens. You have to click the Dashboard button.

It might be nice if the back button worked and even if the URL updated to reflect which page you were on at any given time (dashboard, upload, purchase, etc).

### Page formatting after selecting credits

The "Complete your purchase" section of the page that loads after you select a credits option has some poor CSS formatting. There's no space between that container and the bottom container on the page, and the buttons aren't centered in the div. Same with the text "Purchase 25 redits for $4.00" which is left-aligned and looks out of place.

### Play stems from the browser

After a job is completed, the user should be able to play the stems from the browser in addition to being able to download individual stems or all of them in a zip file.

### Show the job progress and when it has completed without refreshing

I don't like having to manually hit a refresh button to see if the job is completed. Update the status of the jobs in realtime without refreshing the page.

### Re-brand from "ReStem" to "Mux-minus"

The project has a new name "Mux Minus" which is a play on words related to "mix-minus" and muxing / demuxing. I haven't decided on whether the branding should be "MuxMinus" or "Mux-Minus" or "Mux-minus" or "Mux Minus" or "Mux-" or "mux-". Perhaps you can think it over and decide what makes the most sense? The domain name is "muxminus.com".

### Choose between 4 stems or 2 stems

It is possible to choose between 4 stems or 2 stems, but the resulting job still produces the standard 4 stem output.

To fix this, we need to make sure to call the `demucs` CLI with the correct argument when doing a two-stem job. The docs show the example...

```
# If you only want to separate vocals out of an audio, use `--two-stems=vocals` (You can also set to drums or bass)
demucs --two-stems=vocals myfile.mp3
```

Find the problem and make sure the job is processed as a two-stem job with the correct stem option (vocals, bass, or drums), and make sure that the browser playback shows only two playback options for two-stem jobs.

### Error when refreshing dashboard after server restart

When developing, if I have the web page loaded at http://localhost:8000/dashboard, then I rebuild and restart the backend service, I get the following error when refreshing the web UI:

```
{"detail":"Not Found"}
```

But if I remove "dashboard" from the URL path, the page loads and the route is back at dashboard again.

Also if you are not logged in, and you try to go to the dashboard url, you get the same message when ideally you just get redirected to the login page.

### Add landing page

Instead of the front page being a login / registration form, I want the front page to look like a typical landing page with a hero, information, examples, and a call to action to register / login.

The front page should...

- Inform the user what this app does, and that it uses a free open source MIT licensed demucs project with a link to the GitHub repo.
- Provide the user with an original song that is playable in the browser, along with that song broken down into stems that are individually playable as well. That way they get a playable example in the browser of what the app does.

### Job polling results in the collapse of View/Play content

If you expand a completed job by clicking View/Play while a job is processing, after a few seconds the content collapses and you have to click "View/Play" again. I think it's related to the job polling behavior?

