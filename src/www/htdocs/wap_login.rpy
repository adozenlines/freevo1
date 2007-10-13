# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# wap_login.rpy - Wap interface login form.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:
#
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2003 Krister Lagerstrom, et al.
# Please see the file freevo/Docs/CREDITS for a complete list of authors.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------

from www.wap_types import WapResource, FreevoWapResource

class WLoginResource(FreevoWapResource):

    def _render(self, request):

        fv = WapResource()
        form = request.args

        user = fv.formValue(form, 'user')
        passw = fv.formValue(form, 'passw')
        action = fv.formValue(form, 'action')

        fv.printHeader()

        fv.res += '  <card id="card1" title="Freevo Wap">\n'
        fv.res += '   <p><big><strong>Freevo Wap Login</strong></big></p>\n'

        if action <> "submit":

            fv.res += '       <p>User : <input name="user" title="User" size="15"/><br/>\n'
            fv.res += '          Passw : <input name="passw" type="password" title="Password" size="15"/></p>\n'
            fv.res += '   <do type="accept" label="Login">\n'
            fv.res += '     <go href="wap_rec.rpy" method="post">\n'
            fv.res += '       <postfield name="u" value="$user"/>\n'
            fv.res += '       <postfield name="p" value="$passw"/>\n'
            fv.res += '     </go>\n'
            fv.res += '   </do>\n'
            fv.res += '  </card>\n'

        fv.printFooter()

        return String( fv.res )

resource = WLoginResource()
