-- Vertically merge a leading run of cells in column 1 of every table body.
-- A non-empty column-1 cell starts a span; immediately following blank column-1
-- cells continue it. This is the "Parameter group" pattern used by the grouped
-- parameter tables (group name in the first row of the group, blanks below), so
-- the markdown stays a clean pipe table and the merge happens only in the
-- rendered docx.
local stringify = pandoc.utils.stringify

local function is_blank(cell)
  return stringify(cell.contents):match("^%s*$") ~= nil
end

function Table(tbl)
  for _, body in ipairs(tbl.bodies) do
    local rows = body.body
    local i = 1
    while i <= #rows do
      local span = 1
      while i + span <= #rows and is_blank(rows[i + span].cells[1]) do
        span = span + 1
      end
      if span > 1 and not is_blank(rows[i].cells[1]) then
        rows[i].cells[1].row_span = span
        for k = i + 1, i + span - 1 do
          table.remove(rows[k].cells, 1)
        end
      end
      i = i + span
    end
  end
  return tbl
end
