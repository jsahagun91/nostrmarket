function loadTemplateAsync(path) {
  const result = new Promise(resolve => {
    const xhttp = new XMLHttpRequest()

    xhttp.onreadystatechange = function () {
      if (this.readyState == 4) {
        if (this.status == 200) resolve(this.responseText)

        if (this.status == 404) resolve(`<div>Page not found: ${path}</div>`)
      }
    }

    xhttp.open('GET', path, true)
    xhttp.send()
  })

  return result
}

<<<<<<< HEAD
function imgSizeFit(img, maxWidth = 1024, maxHeight = 768) {
  let ratio = Math.min(
    1,
    maxWidth / img.naturalWidth,
    maxHeight / img.naturalHeight
  )
  return {width: img.naturalWidth * ratio, height: img.naturalHeight * ratio}
}

=======
>>>>>>> customer-stallUI
async function hash(string) {
  const utf8 = new TextEncoder().encode(string)
  const hashBuffer = await crypto.subtle.digest('SHA-256', utf8)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  const hashHex = hashArray
    .map(bytes => bytes.toString(16).padStart(2, '0'))
    .join('')
  return hashHex
}

function isJson(str) {
  if (typeof str !== 'string') {
    return false
  }
  try {
    JSON.parse(str)
    return true
  } catch (error) {
    return false
  }
}

function timeFromNow(time) {
  // Get timestamps
  let unixTime = new Date(time).getTime()
  if (!unixTime) return
  let now = new Date().getTime()

  // Calculate difference
  let difference = unixTime / 1000 - now / 1000

  // Setup return object
  let tfn = {}

  // Check if time is in the past, present, or future
  tfn.when = 'now'
  if (difference > 0) {
    tfn.when = 'future'
  } else if (difference < -1) {
    tfn.when = 'past'
  }

  // Convert difference to absolute
  difference = Math.abs(difference)

  // Calculate time unit
  if (difference / (60 * 60 * 24 * 365) > 1) {
    // Years
    tfn.unitOfTime = 'years'
    tfn.time = Math.floor(difference / (60 * 60 * 24 * 365))
  } else if (difference / (60 * 60 * 24 * 45) > 1) {
    // Months
    tfn.unitOfTime = 'months'
    tfn.time = Math.floor(difference / (60 * 60 * 24 * 45))
  } else if (difference / (60 * 60 * 24) > 1) {
    // Days
    tfn.unitOfTime = 'days'
    tfn.time = Math.floor(difference / (60 * 60 * 24))
  } else if (difference / (60 * 60) > 1) {
    // Hours
    tfn.unitOfTime = 'hours'
    tfn.time = Math.floor(difference / (60 * 60))
  } else if (difference / 60 > 1) {
    // Minutes
    tfn.unitOfTime = 'minutes'
    tfn.time = Math.floor(difference / 60)
  } else {
    // Seconds
    tfn.unitOfTime = 'seconds'
    tfn.time = Math.floor(difference)
  }

  // Return time from now data
  return `${tfn.time} ${tfn.unitOfTime}`
}
