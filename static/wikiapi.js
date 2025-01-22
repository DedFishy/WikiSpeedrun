const API_BASE = "https://api.wikimedia.org/core/v1/wikipedia/en/";
const USER_AGENT = "Wikipedia Speedrun Game/0.0 (boynegregg312@gmail.com) JavaScript Fetch"

async function getPageHTML(page_id) {
    let page_url = API_BASE + "page/" + page_id + "/bare"
    let page_response = await fetch(page_url,
        {
            headers: {
                'Api-User-Agent': USER_AGENT
            }
        }
    )
    let page_response_data = await page_response.json();
    console.log(page_response_data);
    if (page_response.hasOwnProperty("httpCode") && page_response["httpCode"] != 200) {
        console.log("load failed");
        return {"success": false}
    }

    if (page_response_data.hasOwnProperty("redirect_target")) {
        return await getPageHTML(page_response_data["redirect_target"]
                                 .replace("/w/rest.php/v1/page/", "")
                                 .replace("/bare", "")
        )
    }



    let content_url = API_BASE + "page/" + page_id + "/html";
    let content_response = await fetch(content_url,
        {
            headers: {
                'Api-User-Agent': USER_AGENT
            }
        }
    );
    let content_response_data = await content_response.text();
    content_response_data = content_response_data
                            .replaceAll('<base href="//en.wikipedia.org/wiki/"/>', "")
                            .replaceAll("./", "https://en.wikipedia.org/wiki/")
                            .replaceAll("/w/load.php", "https://en.wikipedia.org/w/load.php")
    return {
        "html": content_response_data,
        "title": page_response_data["title"],
        "success": true
    };
}