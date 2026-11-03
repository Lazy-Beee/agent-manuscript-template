-- caption_style.lua
-- Style figure/table captions distinctly from body text.
--
-- The manuscript writes captions as plain paragraphs that begin "Figure N. ..."
-- or "Table N. ...", so pandoc renders them in the Body Text style, identical to
-- the surrounding prose. This filter tags each such paragraph with the Word
-- "Image Caption" / "Table Caption" paragraph style (sized by the bundled
-- reference doc's Caption style) and bolds only the "Figure N." / "Table N."
-- label, leaving the rest of the caption at regular weight. It also tags image-only
-- paragraphs with the centred, keep-with-next "Captioned Figure" style (see below).
--
-- A paragraph counts as a caption only when the number token immediately after
-- the keyword ends with a period ("Figure 5.", "Table 1."). In-text references
-- such as "Figure 10 shows ..." or "Figure 8d and 8e ..." have no trailing period
-- on the number and are left untouched.

local function caption_kind(inlines)
  -- Match numeric captions ("Figure 5.", "Table 1.") and appendix captions with a
  -- letter prefix, written either without or with a separating period ("Figure A1.",
  -- "Figure A.1.", "Table B2."). The trailing period distinguishes a real caption
  -- from an in-text reference ("Figure 10 shows ...", "Figure A.3(b) shows ...").
  local s = pandoc.utils.stringify(inlines)
  if s:match("^Figure%s+%u?%.?%d+%.") then return "Image Caption" end
  if s:match("^Table%s+%u?%.?%d+%.") then return "Table Caption" end
  return nil
end

-- Bold the leading label: every inline up to and including the first Str that
-- ends with a period (the "N." token). Returns the rewritten inline list.
local function bold_label(inlines)
  local out = {}
  local label = {}
  local closed = false
  for _, inl in ipairs(inlines) do
    if closed then
      out[#out + 1] = inl
    else
      label[#label + 1] = inl
      if inl.t == "Str" and inl.text:match("%.$") then
        out[#out + 1] = pandoc.Strong(label)
        closed = true
      end
    end
  end
  -- No period token found: leave the collected inlines unbolded, as-is.
  if not closed then
    for _, inl in ipairs(label) do out[#out + 1] = inl end
  end
  return out
end

-- A paragraph that holds nothing but one image is a figure body. It gets the Word
-- "Captioned Figure" paragraph style (pandoc's own name for an image with a caption
-- below it): based on "Figure", which the bundled reference doc centres, plus
-- keep-with-next so the image never parts from its "Figure N." caption at a page
-- break. Without it the image sits in Body Text, flush left once a figure is
-- narrower than the column (e.g. an image given {width=60%}).
local function is_image_para(inlines)
  local n = 0
  for _, inl in ipairs(inlines) do
    if inl.t == "Image" then
      n = n + 1
    elseif inl.t ~= "Space" and inl.t ~= "SoftBreak" then
      return false
    end
  end
  return n == 1
end

function Para(el)
  if is_image_para(el.content) then
    return pandoc.Div({ el }, pandoc.Attr("", {}, { ["custom-style"] = "Captioned Figure" }))
  end
  local kind = caption_kind(el.content)
  if not kind then return nil end
  local styled = pandoc.Para(bold_label(el.content))
  return pandoc.Div({ styled }, pandoc.Attr("", {}, { ["custom-style"] = kind }))
end
