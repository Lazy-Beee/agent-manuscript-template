-- refs_left.lua
-- Keep the reference list left-aligned while the body stays justified.
--
-- The bundled reference doc justifies "Body Text", which pandoc assigns to every
-- plain paragraph, so the hand-numbered reference entries would be justified too.
-- Justifying an entry stretches the gaps around its author initials, page range,
-- and DOI, which reads badly. This filter tags each entry with the Word
-- "Bibliography" style, which the reference doc keeps at the body font and
-- spacing but left-aligned.
--
-- Every paragraph after the "References" heading counts as an entry, up to the
-- horizontal rule that a -Jpg render inserts before its figure note (the note is
-- not a reference and keeps the body style).

local function is_refs_heading(blk)
  local text = pandoc.utils.stringify(blk):gsub("^%s*(.-)%s*$", "%1"):lower()
  return text == "references"
end

function Pandoc(doc)
  local blocks = {}
  local in_refs = false
  for _, blk in ipairs(doc.blocks) do
    if blk.t == "Header" then
      in_refs = is_refs_heading(blk)
    elseif blk.t == "HorizontalRule" then
      in_refs = false
    elseif in_refs and blk.t == "Para" then
      blk = pandoc.Div({ blk }, pandoc.Attr("", {}, { ["custom-style"] = "Bibliography" }))
    end
    blocks[#blocks + 1] = blk
  end
  return pandoc.Pandoc(blocks, doc.meta)
end
