-- Right-aligned equation numbers for DOCX. A display equation whose TeX contains
-- \tag{N} is rewritten as a borderless 2-column table: equation (centered) on the
-- left, (N) right-aligned on the right. \tag{N} is also the standard MathJax way to
-- right-align a number, so the same markdown source previews correctly too.
function Para(el)
  if #el.content ~= 1 then return nil end
  local m = el.content[1]
  if not (m.t == "Math" and m.mathtype == "DisplayMath") then return nil end
  local num = m.text:match("\\tag%s*{([%w%.%-]+)}")
  if not num then return nil end
  m.text = m.text:gsub("%s*\\tag%s*{[%w%.%-]+}%s*", " "):gsub("%s+$", "")

  local eqCell  = pandoc.Cell(pandoc.Blocks{ pandoc.Para{ m } }, "AlignCenter")
  local numCell = pandoc.Cell(pandoc.Blocks{ pandoc.Para{ pandoc.Str("(" .. num .. ")") } }, "AlignRight")
  local row = pandoc.Row{ eqCell, numCell }
  local colspecs = { {"AlignCenter", 0.86}, {"AlignRight", 0.14} }
  return pandoc.Table(
    pandoc.Caption(pandoc.Blocks{}),
    colspecs,
    pandoc.TableHead{},
    { pandoc.TableBody{ row } },
    pandoc.TableFoot{}
  )
end
